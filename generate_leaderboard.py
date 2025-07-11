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
            elif model_name.startswith('grok'):
                provider = 'xai'
            else:
                provider = 'unknown'
            
            # Clean up model display name
            display_name = model_name.replace('-', ' ').replace('_', ' ')
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            # Parse scores from CSV summary (but we'll recalculate min/max)
            try:
                avg_score = float(row['average_score'])
                median_score = float(row['median_score'])
                min_score_csv = float(row['min_score'])  # Keep for reference
                max_score_csv = float(row['max_score'])  # Keep for reference
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
                'minScore': min_score_csv,  # Will recalculate later
                'maxScore': max_score_csv,  # Will recalculate later
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
    
    # Recalculate min/max based on actual displayed scores (handles duplicates consistently)
    for model in models:
        model_scores = []
        for comic_id, scores in comic_scores.items():
            if model['model_id'] in scores and scores[model['model_id']] is not None:
                model_scores.append(scores[model['model_id']])
        
        if model_scores:
            model['minScore'] = min(model_scores)
            model['maxScore'] = max(model_scores)
            # Also recalculate average to ensure consistency
            model['avgScore'] = sum(model_scores) / len(model_scores)
    
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
    
    # Load detailed results for modal display
    # Note: Use the last occurrence if there are duplicates (most recent/successful run)
    detailed_results = {}
    if os.path.exists('benchmark_details.json'):
        with open('benchmark_details.json', 'r') as f:
            benchmark_data = json.load(f)
            for result in benchmark_data.get('detailed_results', []):
                comic_id = result.get('comic_id')
                if comic_id:
                    detailed_results[comic_id] = result
    
    # Convert detailed results to JSON for JavaScript
    detailed_results_json = json.dumps(detailed_results, indent=2)
    
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
        
        row_html = f'<tr data-comic="{comic_title}"><td class="comic-name"><a href="{comic_url}" target="_blank">{comic_title}</a></td>'
        
        # Calculate average score for this comic
        scores_for_comic = []
        
        # Add scores for each model
        for model in models:
            score = comic_scores[comic_id].get(model['model_id'])
            if score is not None:
                scores_for_comic.append(score)
                score_class = 'high' if score >= 7 else 'medium' if score >= 5 else 'low'
                row_html += f'<td class="score {score_class} clickable" data-score="{score}" data-comic="{comic_id}" data-model="{model["model_id"]}">{score:.1f}</td>'
            else:
                row_html += '<td class="score" data-score="-1">-</td>'
        
        # Add average score
        if scores_for_comic:
            avg_score = sum(scores_for_comic) / len(scores_for_comic)
            avg_class = 'high' if avg_score >= 7 else 'medium' if avg_score >= 5 else 'low'
            row_html += f'<td class="score avg-score {avg_class}" data-score="{avg_score}">{avg_score:.2f}</td>'
        else:
            row_html += '<td class="score avg-score" data-score="-1">-</td>'
        
        row_html += '</tr>'
        comic_table_rows.append(row_html)
    
    comic_table_html = '\n'.join(comic_table_rows)
    
    # Generate model header cells
    model_headers = ''.join([f'<th class="model-header sortable" data-sort="model-{i}">{model["model"]}</th>' for i, model in enumerate(models)])
    
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
            padding: 25px 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2rem; margin: 0; font-weight: 700; }}
        
        /* Intro section */
        .about-section {{
            padding: 30px;
            background: white;
            margin: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            line-height: 1.6;
        }}
        
        .about-section p {{
            color: #666;
            margin-bottom: 10px;
            text-align: left;
            max-width: 700px;
        }}
        
        .about-section ul {{
            max-width: 700px;
            margin: 20px auto;
            text-align: left;
        }}
        
        .about-section a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .about-section a:hover {{
            text-decoration: underline;
        }}
        
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
        
        .avg-header {{
            font-weight: 700;
            background: linear-gradient(135deg, #2c3e50, #34495e) !important;
        }}
        
        .avg-score {{
            font-weight: 700;
            border-left: 2px solid #ddd;
        }}
        
        .sortable {{
            cursor: pointer;
            user-select: none;
        }}
        
        .sortable:hover {{
            background: linear-gradient(135deg, #2980b9, #3498db) !important;
        }}
        
        .clickable {{
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .clickable:hover {{
            transform: scale(1.1);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            border-radius: 4px;
        }}
        
        /* Modal styles */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 0;
            border-radius: 15px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        
        .modal-header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 20px;
            border-radius: 15px 15px 0 0;
        }}
        
        .modal-header h3 {{
            margin: 0;
            font-size: 1.3rem;
        }}
        
        .close {{
            color: white;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            line-height: 1;
        }}
        
        .close:hover {{
            opacity: 0.7;
        }}
        
        .modal-body {{
            padding: 20px;
        }}
        
        .section {{
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            background: #f8f9fa;
        }}
        
        .section h4 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }}
        
        .section p {{
            margin: 0;
            line-height: 1.5;
        }}
        
        .score-breakdown {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }}
        
        .score-item {{
            background: white;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
            border: 1px solid #ddd;
        }}
        
        .score-item .label {{
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .score-item .value {{
            font-size: 1.2rem;
            font-weight: 700;
            color: #2c3e50;
            margin-top: 3px;
        }}
        
        /* Markdown content styling */
        .markdown-content {{
            line-height: 1.6;
            color: #333;
        }}
        
        .markdown-content p {{
            margin: 0 0 10px 0;
        }}
        
        .markdown-content ul, .markdown-content ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        
        .markdown-content li {{
            margin-bottom: 5px;
        }}
        
        .markdown-content strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        
        .markdown-content em {{
            font-style: italic;
        }}
        
        .markdown-content code {{
            background: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.9em;
        }}
        
        .markdown-content blockquote {{
            border-left: 3px solid #3498db;
            padding-left: 15px;
            margin: 10px 0;
            color: #666;
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
        .xai {{ background: #f3e5f5; color: #6a1b9a; }}
        
        .methodology {{
            padding: 30px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
            font-size: 0.9rem;
            line-height: 1.6;
        }}
        .methodology h3 {{ 
            color: #2c3e50; 
            margin-bottom: 20px; 
            font-size: 1.4rem;
            text-align: center;
        }}
        .methodology h4 {{
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }}
        .methodology p {{ 
            color: #666; 
            margin-bottom: 10px; 
        }}
        .methodology a {{
            color: #3498db;
            text-decoration: none;
        }}
        .methodology a:hover {{
            text-decoration: underline;
        }}
        .methodology ul, .methodology ol {{
            margin: 10px 0;
            padding-left: 20px;
            color: #666;
        }}
        .methodology li {{
            margin-bottom: 8px;
        }}
        
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
            <h1>🎨 PBF-Bench</h1>
            <b>Evaluating AI Models on Visual Understanding and Comic Explanations</b>
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
                            <th class="comic-name sortable" data-sort="comic">Comic ↕</th>
                            {model_headers}
                            <th class="avg-header sortable" data-sort="average">Average ↕</th>
                        </tr>
                    </thead>
                    <tbody>
                        {comic_table_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="about-section">
            <div style="text-align: center; margin-right: auto; margin-left: auto; margin-bottom: 30px;">
                <a href="https://pbfcomics.com/comics/trunkle/" target="_blank">
                    <img src="pbf-sample.png" alt="Sample PBF Comic" style="max-width: 600px; width: 100%; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                </a>
                <p style="font-size: 0.85rem; color: #666; margin-top: 8px; text-align: center; margin-left: auto; margin-right: auto;">Example: "Trunkle" - A wordless comic requiring pure visual understanding</p>
            </div>
            
            <div>
                <p>The PBF Comics Benchmark evaluates AI models on {total_comics} comics from Nicholas Gurewitch's <a href="https://pbfcomics.com/" target="_blank">Perry Bible Fellowship</a>. These comics are ideal for testing visual understanding because:</p>
                <ul style="margin: 10px 0; padding-left: 20px; color: #666;">
                    <li><strong>Highly visual:</strong> Unlike text-heavy comics (XKCD, SMBC), many PBF comics <a href="https://pbfcomics.com/comics/trunkle/" target="_blank">contain no words at all</a></li>
                    <li><strong>Diverse styles:</strong> Mix of <a href="https://pbfcomics.com/comics/dinosaur-sheriff/" target="_blank">black-and-white</a>, <a href="https://pbfcomics.com/comics/clear-boundaries/" target="_blank">watercolor</a>, <a href="https://pbfcomics.com/comics/the-shrink-ray/" target="_blank">cartoon</a>, and <a href="https://pbfcomics.com/comics/carolyn-vert/" target="_blank">realistic</a> art</li>
                    <li><strong>Complex themes:</strong> From <a href="https://pbfcomics.com/comics/mrs-hammer/" target="_blank">slapstick humor</a> to <a href="https://pbfcomics.com/comics/atlantis/" target="_blank">pop culture subversions</a></li>
                    <li><strong>Not memorized:</strong> Individual comics lack enough online discussion for models to memorize explanations</li>
                </ul>
            </div>
        </div>

        <div class="methodology">
            <h3>📊 Methodology</h3>
            
            <h4 style="margin-top: 20px; color: #2c3e50;">Ground Truth Creation</h4>
            <p>Each comic received a human-curated explanation by:</p>
            <ol style="margin: 10px 0; padding-left: 20px; color: #666;">
                <li>Generating candidate explanations from GPT-4o, Claude 3.5 Sonnet, and Gemini 2.0 Flash</li>
                <li>Human labeler selecting the best candidate or writing a custom explanation</li>
                <li>Most labels received moderate to significant human modifications</li>
            </ol>
            
            <h4 style="margin-top: 20px; color: #2c3e50;">Scoring Methodology</h4>
            <p>Models explain each comic with: <em>"Explain this comic. Describe what's happening and explain the humor or message."</em></p>
            <p><a href="https://arxiv.org/abs/2306.05685" target="_blank">Claude 4 Opus judges</a> each explanation on:</p>
            <ul style="margin: 10px 0; padding-left: 20px; color: #666;">
                <li><strong>Accuracy (40%):</strong> Correctly identifies what's happening</li>
                <li><strong>Completeness (25%):</strong> Covers all important visual elements</li>
                <li><strong>Insight (25%):</strong> Understands the humor or message</li>
                <li><strong>Clarity (10%):</strong> Well-written and easy to understand</li>
            </ul>
        </div>

        <div class="footer">
            <p>📈 Last updated: <span id="last-updated"></span></p>
            <p>🔗 <a href="https://github.com/andrewkchan/pbf-bench" target="_blank">View on GitHub</a></p>
        </div>
    </div>

    <!-- Include marked.js for markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

    <!-- Modal for detailed view -->
    <div id="detailModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="close">&times;</span>
                <h3 id="modalTitle">Model Response Details</h3>
            </div>
            <div class="modal-body">
                <div class="section">
                    <h4>📊 Score Breakdown</h4>
                    <div class="score-breakdown" id="scoreBreakdown">
                        <!-- Score items will be populated by JavaScript -->
                    </div>
                </div>
                
                <div class="section">
                    <h4>🤖 Model Response</h4>
                    <div id="modelResponse" class="markdown-content">Loading...</div>
                </div>
                
                <div class="section">
                    <h4>⚖️ Judge's Reasoning</h4>
                    <div id="judgeReasoning" class="markdown-content">Loading...</div>
                </div>
                
                <div class="section">
                    <h4>✅ Ground Truth</h4>
                    <div id="groundTruth" class="markdown-content">Loading...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const benchmarkData = {models_json};
        const detailedResults = {detailed_results_json};

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
            initializeSorting();
            initializeModal();
        }});
        
        function initializeModal() {{
            const modal = document.getElementById('detailModal');
            const closeBtn = document.querySelector('.close');
            
            // Close modal when clicking X
            closeBtn.onclick = function() {{
                modal.style.display = 'none';
            }}
            
            // Close modal when clicking outside
            window.onclick = function(event) {{
                if (event.target == modal) {{
                    modal.style.display = 'none';
                }}
            }}
            
            // Add click handlers to score cells
            document.addEventListener('click', function(event) {{
                if (event.target.classList.contains('clickable')) {{
                    const comicId = event.target.dataset.comic;
                    const modelId = event.target.dataset.model;
                    showDetailModal(comicId, modelId);
                }}
            }});
        }}
        
        function showDetailModal(comicId, modelId) {{
            const modal = document.getElementById('detailModal');
            const result = detailedResults[comicId];
            
            if (!result) {{
                alert('No detailed data available for this comic.');
                return;
            }}
            
            // Find model display name
            const model = benchmarkData.find(m => m.model_id === modelId);
            const modelName = model ? model.model : modelId;
            
            // Update modal title
            const comicTitle = result.comic_title || comicId.replace('.png', '');
            document.getElementById('modalTitle').textContent = `${{modelName}} - ${{comicTitle}}`;
            
            // Get explanation and scores for this model
            const explanation = result.explanations[modelId] || 'No explanation available';
            const scores = result.scores[modelId];
            
            // Update content with markdown rendering
            document.getElementById('modelResponse').innerHTML = marked.parse(explanation);
            document.getElementById('groundTruth').innerHTML = marked.parse(result.ground_truth || 'No ground truth available');
            
            if (scores) {{
                document.getElementById('judgeReasoning').innerHTML = marked.parse(scores.reasoning || 'No reasoning available');
                
                // Update score breakdown
                const scoreBreakdown = document.getElementById('scoreBreakdown');
                scoreBreakdown.innerHTML = `
                    <div class="score-item">
                        <div class="label">Overall</div>
                        <div class="value">${{scores.overall_score.toFixed(1)}}</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Accuracy</div>
                        <div class="value">${{scores.accuracy_score.toFixed(1)}}</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Completeness</div>
                        <div class="value">${{scores.completeness_score.toFixed(1)}}</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Insight</div>
                        <div class="value">${{scores.insight_score.toFixed(1)}}</div>
                    </div>
                    <div class="score-item">
                        <div class="label">Clarity</div>
                        <div class="value">${{scores.clarity_score.toFixed(1)}}</div>
                    </div>
                `;
            }} else {{
                document.getElementById('judgeReasoning').innerHTML = marked.parse('No scoring data available');
                document.getElementById('scoreBreakdown').innerHTML = '<p>No scores available</p>';
            }}
            
            // Show modal
            modal.style.display = 'block';
        }}
        
        function initializeSorting() {{
            const table = document.querySelector('.comic-table');
            const tbody = table.querySelector('tbody');
            const headers = table.querySelectorAll('.sortable');
            let currentSort = {{ column: null, ascending: true }};
            
            headers.forEach(header => {{
                header.addEventListener('click', () => {{
                    const sortType = header.dataset.sort;
                    const ascending = currentSort.column === sortType ? !currentSort.ascending : true;
                    currentSort = {{ column: sortType, ascending }};
                    
                    // Update header text to show sort direction
                    headers.forEach(h => {{
                        const text = h.textContent.replace(' ↑', '').replace(' ↓', '').replace(' ↕', '');
                        if (h === header) {{
                            h.textContent = text + (ascending ? ' ↑' : ' ↓');
                        }} else {{
                            h.textContent = text + ' ↕';
                        }}
                    }});
                    
                    // Sort the rows
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    rows.sort((a, b) => {{
                        let aVal, bVal;
                        
                        if (sortType === 'comic') {{
                            aVal = a.dataset.comic.toLowerCase();
                            bVal = b.dataset.comic.toLowerCase();
                        }} else if (sortType === 'average') {{
                            aVal = parseFloat(a.querySelector('.avg-score').dataset.score);
                            bVal = parseFloat(b.querySelector('.avg-score').dataset.score);
                        }} else if (sortType.startsWith('model-')) {{
                            const modelIndex = parseInt(sortType.split('-')[1]);
                            aVal = parseFloat(a.querySelectorAll('.score:not(.avg-score)')[modelIndex].dataset.score);
                            bVal = parseFloat(b.querySelectorAll('.score:not(.avg-score)')[modelIndex].dataset.score);
                        }}
                        
                        // Handle missing values
                        if (aVal === -1) aVal = ascending ? Infinity : -Infinity;
                        if (bVal === -1) bVal = ascending ? Infinity : -Infinity;
                        
                        if (typeof aVal === 'string') {{
                            return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                        }} else {{
                            return ascending ? aVal - bVal : bVal - aVal;
                        }}
                    }});
                    
                    // Re-append sorted rows
                    rows.forEach(row => tbody.appendChild(row));
                }});
            }});
        }}
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