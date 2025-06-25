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
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
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
    
    # Sort by average score (descending) and add ranks
    models.sort(key=lambda x: x['avgScore'], reverse=True)
    for i, model in enumerate(models, 1):
        model['rank'] = i
    
    return models

def create_leaderboard_html(models):
    """Create the complete HTML content"""
    # Convert models data to JSON for JavaScript
    models_json = json.dumps(models, indent=2)
    
    total_comics = models[0]['totalComics'] if models else 0
    
    # Read the template file
    template_path = "docs/index.html"
    if os.path.exists(template_path):
        with open(template_path, 'r') as f:
            html_content = f.read()
        
        # Replace the benchmark data in the JavaScript
        start_marker = "const benchmarkData = ["
        end_marker = "];"
        
        start_idx = html_content.find(start_marker)
        if start_idx != -1:
            end_idx = html_content.find(end_marker, start_idx)
            if end_idx != -1:
                # Replace the data
                new_content = (html_content[:start_idx] + 
                             f"const benchmarkData = {models_json};" + 
                             html_content[end_idx + len(end_marker):])
                return new_content
    
    # If template doesn't exist or parsing failed, create from scratch
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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; font-weight: 700; }}
        .header p {{ font-size: 1.1rem; opacity: 0.9; max-width: 600px; margin: 0 auto; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}
        .stat-number {{ font-size: 2rem; font-weight: 700; color: #2c3e50; margin-bottom: 5px; }}
        .stat-label {{ color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
        .leaderboard {{ padding: 0 30px 30px; }}
        .leaderboard h2 {{ font-size: 1.8rem; margin-bottom: 20px; color: #2c3e50; text-align: center; }}
        .table-container {{ overflow-x: auto; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th {{
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f8f9fa; }}
        .rank {{ font-weight: 700; color: #2c3e50; width: 60px; }}
        .model-name {{ font-weight: 600; color: #2c3e50; min-width: 180px; }}
        .score {{ font-weight: 600; text-align: center; width: 80px; }}
        .score.high {{ color: #27ae60; }}
        .score.medium {{ color: #f39c12; }}
        .score.low {{ color: #e74c3c; }}
        .provider-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}
        .anthropic {{ background: #e8f5e8; color: #2d5a2d; }}
        .google {{ background: #e3f2fd; color: #1565c0; }}
        .openai {{ background: #fff3e0; color: #e65100; }}
        .methodology {{
            padding: 30px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
        }}
        .methodology h3 {{ color: #2c3e50; margin-bottom: 15px; }}
        .methodology p {{ color: #666; margin-bottom: 10px; }}
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .footer a {{ color: #3498db; text-decoration: none; }}
        .footer a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 PBF Comics AI Benchmark</h1>
            <p>Evaluating AI models on comic explanation tasks using Perry Bible Fellowship comics as ground truth</p>
        </div>

        <div class="stats" id="stats"></div>

        <div class="leaderboard">
            <h2>🏆 Leaderboard</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="rank">Rank</th>
                            <th class="model-name">Model</th>
                            <th class="score">Avg Score</th>
                            <th class="score">Median</th>
                            <th class="score">Best</th>
                            <th class="score">Worst</th>
                            <th class="score">Comics</th>
                        </tr>
                    </thead>
                    <tbody id="leaderboard-body"></tbody>
                </table>
            </div>
        </div>

        <div class="methodology">
            <h3>📊 Methodology</h3>
            <p><strong>Dataset:</strong> {total_comics} Perry Bible Fellowship comics with human-curated ground truth explanations</p>
            <p><strong>Evaluation:</strong> AI explanations are scored by Claude-4-Opus on accuracy (40%), completeness (25%), insight (25%), and clarity (10%)</p>
            <p><strong>Scoring:</strong> Each criterion is rated 1-10, with the overall score being a weighted average</p>
            <p><strong>Ground Truth:</strong> Created using candidate explanations from Claude-3.5-Sonnet, Gemini-2.0-Flash, and GPT-4o, then human-selected via web interface</p>
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
                    <div class="stat-label">AI Models</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{totalComics}}</div>
                    <div class="stat-label">Comics Tested</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{avgScore}}</div>
                    <div class="stat-label">Average Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{bestScore}}</div>
                    <div class="stat-label">Highest Score</div>
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
                    <td class="score">${{model.totalComics}}</td>
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
    parser.add_argument('--output', default='docs/index.html',
                       help='Output HTML file')
    
    args = parser.parse_args()
    
    try:
        models = load_benchmark_data(args.csv)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        # Generate HTML
        html_content = create_leaderboard_html(models)
        
        # Write the HTML file
        with open(args.output, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Generated leaderboard: {args.output}")
        print(f"📊 {len(models)} models, {models[0]['totalComics'] if models else 0} comics")
        if models:
            print(f"🥇 Winner: {models[0]['model']} ({models[0]['avgScore']:.2f})")
        
    except Exception as e:
        print(f"❌ Error generating leaderboard: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())