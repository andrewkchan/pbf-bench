#!/usr/bin/env python3
"""
Generate static leaderboard HTML page from benchmark results.
Updates the leaderboard with current benchmark data.
"""
import os
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path

def load_benchmark_data(csv_file="benchmark_results.csv"):
    """Load benchmark data from CSV file"""
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Benchmark results file not found: {csv_file}")
    
    models = []
    comic_scores = {}  # Store per-comic scores
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        # Extract comic columns
        comic_columns = [col for col in headers if col.startswith('comic_')]
        
        for row in reader:
            if not row['model_name']:  # Skip empty rows
                continue
                
            # Determine provider from model name
            model_name = row['model_name']
            if model_name.startswith('claude'):
                provider = 'anthropic'
            elif model_name.startswith('gemini'):
                provider = 'google'
            elif model_name.startswith(('gpt', 'o3', 'o4')):
                provider = 'openai'
            else:
                provider = 'unknown'
            
            # Clean up model display name
            display_name = model_name.replace('-', ' ').replace('_', ' ')
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            # Parse scores
            try:
                avg_score = float(row['average_score'])
                median_score = float(row['median_score'])
                min_score = float(row['min_score'])
                max_score = float(row['max_score'])
                total_comics = int(row['total_comics'])
            except (ValueError, KeyError):
                print(f"Warning: Invalid data for model {model_name}, skipping")
                continue
            
            models.append({
                'model': display_name,
                'model_id': model_name,
                'provider': provider,
                'version': row.get('model_version', model_name),
                'avgScore': avg_score,
                'medianScore': median_score,
                'minScore': min_score,
                'maxScore': max_score,
                'totalComics': total_comics,
                'timestamp': row.get('timestamp', '')
            })
            
            # Store individual comic scores
            for comic_col in comic_columns:
                comic_id = comic_col.replace('comic_', '')
                if comic_id not in comic_scores:
                    comic_scores[comic_id] = {}
                
                try:
                    score = float(row[comic_col])
                    comic_scores[comic_id][model_name] = score
                except (ValueError, TypeError):
                    comic_scores[comic_id][model_name] = None
    
    # Sort by average score (descending) and add ranks
    models.sort(key=lambda x: x['avgScore'], reverse=True)
    for i, model in enumerate(models, 1):
        model['rank'] = i
    
    return models, comic_scores

def load_metadata(metadata_file="pbf_comics_metadata.json"):
    """Load comic metadata for URLs"""
    if not os.path.exists(metadata_file):
        return {}
    
    with open(metadata_file, 'r') as f:
        metadata_list = json.load(f)
    
    # Convert to dict keyed by filename
    metadata_dict = {}
    for comic in metadata_list:
        metadata_dict[comic['filename']] = comic
    
    return metadata_dict

def create_leaderboard_html(models, comic_scores, metadata):
    """Create the complete HTML content"""
    # Convert models data to JSON for JavaScript
    models_json = json.dumps(models, indent=2)
    
    total_comics = models[0]['totalComics'] if models else 0
    
    # Sort comics by filename
    sorted_comics = sorted(comic_scores.keys())
    
    # Create comic scores table HTML
    comic_table_rows = []
    for comic_id in sorted_comics:
        # Get metadata for this comic
        comic_meta = metadata.get(comic_id, {})
        comic_title = comic_meta.get('comic_title', comic_id.replace('.png', '').replace('PBF-', ''))
        comic_url = comic_meta.get('page_url', '#')
        
        row_html = f'<tr><td class="comic-name"><a href="{comic_url}" target="_blank">{comic_title}</a></td>'
        
        # Add scores for each model
        for model in models:
            score = comic_scores[comic_id].get(model['model_id'])
            if score is not None:
                score_class = 'high' if score >= 7 else 'medium' if score >= 5 else 'low'
                row_html += f'<td class="score {score_class}">{score:.1f}</td>'
            else:
                row_html += '<td class="score">-</td>'
        
        row_html += '</tr>'
        comic_table_rows.append(row_html)
    
    comic_table_html = '\n'.join(comic_table_rows)
    
    # Generate model header cells
    model_headers = ''.join([f'<th class="model-header">{model["model"]}</th>' for model in models])
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PBF Comics AI Benchmark Leaderboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 10px; font-weight: 700; }}
        .header p {{ font-size: 1rem; opacity: 0.9; max-width: 600px; margin: 0 auto; }}
        
        /* Compact stats */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 20px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .stat-number {{ font-size: 1.5rem; font-weight: 700; color: #2c3e50; margin-bottom: 3px; }}
        .stat-label {{ color: #666; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }}
        
        /* Compact leaderboard */
        .leaderboard {{ padding: 20px; }}
        .leaderboard h2 {{ font-size: 1.4rem; margin-bottom: 15px; color: #2c3e50; text-align: center; }}
        .leaderboard-table-container {{ 
            overflow-x: auto; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .leaderboard-table {{ width: 100%; border-collapse: collapse; background: white; font-size: 0.9rem; }}
        .leaderboard-table th {{
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
        }}
        .leaderboard-table td {{ padding: 8px; border-bottom: 1px solid #eee; }}
        .leaderboard-table tr:hover {{ background: #f8f9fa; }}
        
        /* Comic scores table */
        .comic-scores {{ padding: 0 20px 20px; }}
        .comic-scores h2 {{ font-size: 1.4rem; margin-bottom: 15px; color: #2c3e50; text-align: center; }}
        .comic-table-container {{ 
            overflow-x: auto; 
            border-radius: 8px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            max-height: 600px;
            overflow-y: auto;
        }}
        .comic-table {{ width: 100%; border-collapse: collapse; background: white; font-size: 0.85rem; }}
        .comic-table th {{
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 10px 6px;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .comic-table td {{ padding: 6px; border-bottom: 1px solid #eee; text-align: center; }}
        .comic-table tr:hover {{ background: #f8f9fa; }}
        
        .comic-name {{ 
            text-align: left !important; 
            font-weight: 500; 
            min-width: 200px;
            position: sticky;
            left: 0;
            background: white;
            z-index: 5;
        }}
        .comic-name a {{ color: #2c3e50; text-decoration: none; }}
        .comic-name a:hover {{ color: #3498db; text-decoration: underline; }}
        
        .model-header {{
            writing-mode: vertical-rl;
            text-orientation: mixed;
            min-width: 40px;
            max-width: 40px;
            height: 120px;
            padding: 10px 2px;
        }}
        
        .rank {{ font-weight: 700; color: #2c3e50; width: 50px; }}
        .model-name {{ font-weight: 600; color: #2c3e50; min-width: 150px; }}
        .score {{ font-weight: 600; text-align: center; width: 60px; }}
        .score.high {{ background-color: #d4edda; color: #155724; }}
        .score.medium {{ background-color: #fff3cd; color: #856404; }}
        .score.low {{ background-color: #f8d7da; color: #721c24; }}
        
        .provider-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            margin-top: 2px;
        }}
        .anthropic {{ background: #e8f5e8; color: #2d5a2d; }}
        .google {{ background: #e3f2fd; color: #1565c0; }}
        .openai {{ background: #fff3e0; color: #e65100; }}
        
        .methodology {{
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
            font-size: 0.9rem;
        }}
        .methodology h3 {{ color: #2c3e50; margin-bottom: 10px; }}
        .methodology p {{ color: #666; margin-bottom: 8px; }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9rem;
        }}
        .footer a {{ color: #3498db; text-decoration: none; }}
        .footer a:hover {{ text-decoration: underline; }}
        
        @media (max-width: 768px) {{
            .model-header {{ font-size: 0.7rem; }}
            .comic-table {{ font-size: 0.75rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 PBF Comics AI Benchmark</h1>
            <p>Evaluating AI models on comic explanation tasks using Perry Bible Fellowship comics</p>
        </div>

        <div class="stats" id="stats"></div>

        <div class="leaderboard">
            <h2>🏆 Leaderboard</h2>
            <div class="leaderboard-table-container">
                <table class="leaderboard-table">
                    <thead>
                        <tr>
                            <th class="rank">Rank</th>
                            <th class="model-name">Model</th>
                            <th class="score">Avg</th>
                            <th class="score">Median</th>
                            <th class="score">Best</th>
                            <th class="score">Worst</th>
                        </tr>
                    </thead>
                    <tbody id="leaderboard-body"></tbody>
                </table>
            </div>
        </div>

        <div class="comic-scores">
            <h2>📊 Detailed Scores by Comic</h2>
            <div class="comic-table-container">
                <table class="comic-table">
                    <thead>
                        <tr>
                            <th class="comic-name">Comic</th>
                            {model_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {comic_table_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="methodology">
            <h3>📊 Methodology</h3>
            <p><strong>Dataset:</strong> {total_comics} Perry Bible Fellowship comics with human-curated ground truth explanations</p>
            <p><strong>Evaluation:</strong> AI explanations scored by Claude-4-Opus on accuracy (40%), completeness (25%), insight (25%), clarity (10%)</p>
            <p><strong>Scoring:</strong> Each criterion rated 1-10, with overall score as weighted average</p>
        </div>

        <div class="footer">
            <p>📈 Last updated: <span id="last-updated"></span></p>
            <p>🔗 <a href="https://github.com/yourusername/pbf-bench" target="_blank">View on GitHub</a> | 
               📊 <a href="../benchmark_results.csv" target="_blank">Download CSV</a> | 
               📄 <a href="../benchmark_details.json" target="_blank">Detailed Results</a></p>
        </div>
    </div>

    <script>
        const benchmarkData = {models_json};

        function getScoreClass(score) {{
            if (score >= 7) return 'high';
            if (score >= 5) return 'medium';
            return 'low';
        }}

        function getMedal(rank) {{
            switch(rank) {{
                case 1: return '🥇';
                case 2: return '🥈';  
                case 3: return '🥉';
                default: return '';
            }}
        }}

        function populateStats() {{
            const totalModels = benchmarkData.length;
            const totalComics = benchmarkData[0]?.totalComics || 0;
            const avgScore = totalModels > 0 ? 
                (benchmarkData.reduce((sum, model) => sum + model.avgScore, 0) / totalModels).toFixed(2) : 0;
            const bestScore = totalModels > 0 ? 
                Math.max(...benchmarkData.map(model => model.maxScore)) : 0;

            document.getElementById('stats').innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${{totalModels}}</div>
                    <div class="stat-label">Models</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{totalComics}}</div>
                    <div class="stat-label">Comics</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{avgScore}}</div>
                    <div class="stat-label">Avg Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{bestScore.toFixed(1)}}</div>
                    <div class="stat-label">Best Score</div>
                </div>
            `;
        }}

        function populateTable() {{
            const tbody = document.getElementById('leaderboard-body');
            
            tbody.innerHTML = benchmarkData.map(model => `
                <tr>
                    <td class="rank">${{getMedal(model.rank)}} ${{model.rank}}</td>
                    <td class="model-name">
                        <div>${{model.model}}</div>
                        <div class="provider-badge ${{model.provider}}">${{model.provider}}</div>
                    </td>
                    <td class="score ${{getScoreClass(model.avgScore)}}">${{model.avgScore.toFixed(2)}}</td>
                    <td class="score ${{getScoreClass(model.medianScore)}}">${{model.medianScore.toFixed(2)}}</td>
                    <td class="score ${{getScoreClass(model.maxScore)}}">${{model.maxScore.toFixed(1)}}</td>
                    <td class="score ${{getScoreClass(model.minScore)}}">${{model.minScore.toFixed(1)}}</td>
                </tr>
            `).join('');
        }}

        function updateLastUpdated() {{
            const now = new Date();
            document.getElementById('last-updated').textContent = now.toLocaleDateString('en-US', {{
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZoneName: 'short'
            }});
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            populateStats();
            populateTable();
            updateLastUpdated();
        }});
    </script>
</body>
</html>"""
    
    return html_content

def main():
    parser = argparse.ArgumentParser(description='Generate PBF Comics AI Benchmark leaderboard')
    parser.add_argument('--csv', default='benchmark_results.csv', 
                       help='Input CSV file with benchmark results')
    parser.add_argument('--metadata', default='pbf_comics_metadata.json',
                       help='Comic metadata JSON file')
    parser.add_argument('--output', default='docs/index.html',
                       help='Output HTML file')
    
    args = parser.parse_args()
    
    try:
        models, comic_scores = load_benchmark_data(args.csv)
        metadata = load_metadata(args.metadata)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        # Generate HTML
        html_content = create_leaderboard_html(models, comic_scores, metadata)
        
        # Write the HTML file
        with open(args.output, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Generated leaderboard: {args.output}")
        print(f"📊 {len(models)} models, {models[0]['totalComics'] if models else 0} comics")
        print(f"📈 {len(comic_scores)} comics with detailed scores")
        if models:
            print(f"🥇 Winner: {models[0]['model']} ({models[0]['avgScore']:.2f})")
        
    except Exception as e:
        print(f"❌ Error generating leaderboard: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())