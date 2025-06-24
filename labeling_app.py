#!/usr/bin/env python3
"""
Web app for labeling ground truth explanations.
Provides a UI to review AI-generated explanations and select the best one.
"""
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from typing import Dict, List, Optional

app = Flask(__name__)

class LabelingApp:
    def __init__(self, 
                 explanations_file: str = "ai_explanations.json",
                 ground_truth_file: str = "ground_truth_labels.json"):
        self.explanations_file = explanations_file
        self.ground_truth_file = ground_truth_file
        
        # Load explanations
        if os.path.exists(explanations_file):
            with open(explanations_file, 'r') as f:
                self.explanations = json.load(f)
        else:
            self.explanations = {}
        
        # Load existing ground truth
        if os.path.exists(ground_truth_file):
            with open(ground_truth_file, 'r') as f:
                self.ground_truth = json.load(f)
        else:
            self.ground_truth = {}
        
        self.comic_ids = list(self.explanations.keys())
    
    def save_ground_truth(self):
        """Save ground truth to file"""
        with open(self.ground_truth_file, 'w') as f:
            json.dump(self.ground_truth, f, indent=2)
    
    def get_comic_data(self, comic_id: str) -> Optional[Dict]:
        """Get comic data for labeling interface"""
        if comic_id not in self.explanations:
            return None
        
        comic_data = self.explanations[comic_id].copy()
        
        # Add ground truth data if available
        if comic_id in self.ground_truth:
            comic_data.update(self.ground_truth[comic_id])
        
        return comic_data
    
    def save_label(self, comic_id: str, selected: str, custom_explanation: str = "") -> bool:
        """Save label for a comic"""
        if comic_id not in self.explanations:
            return False
        
        self.ground_truth[comic_id] = {
            'selected': selected,
            'custom_explanation': custom_explanation,
            'labeled_by': 'human',
            'labeled_at': datetime.utcnow().isoformat()
        }
        
        self.save_ground_truth()
        return True
    
    def get_progress(self) -> Dict:
        """Get labeling progress statistics"""
        total = len(self.comic_ids)
        labeled = len(self.ground_truth)
        return {
            'total': total,
            'labeled': labeled,
            'remaining': total - labeled,
            'percentage': (labeled / total * 100) if total > 0 else 0
        }
    
    def get_next_unlabeled(self, current_id: Optional[str] = None) -> Optional[str]:
        """Get next unlabeled comic ID"""
        if current_id:
            try:
                current_index = self.comic_ids.index(current_id)
                start_index = current_index + 1
            except ValueError:
                start_index = 0
        else:
            start_index = 0
        
        # Look for next unlabeled comic
        for i in range(start_index, len(self.comic_ids)):
            if self.comic_ids[i] not in self.ground_truth:
                return self.comic_ids[i]
        
        # Wrap around to beginning
        for i in range(0, start_index):
            if self.comic_ids[i] not in self.ground_truth:
                return self.comic_ids[i]
        
        return None

# Global labeling app instance
labeling_app = LabelingApp()

@app.route('/')
def index():
    """Main labeling interface"""
    # Get first unlabeled comic
    comic_id = request.args.get('comic_id')
    if not comic_id:
        comic_id = labeling_app.get_next_unlabeled()
    
    if not comic_id:
        # All comics are labeled
        return render_template('complete.html', progress=labeling_app.get_progress())
    
    comic_data = labeling_app.get_comic_data(comic_id)
    if not comic_data:
        return "Comic not found", 404
    
    progress = labeling_app.get_progress()
    current_index = labeling_app.comic_ids.index(comic_id) + 1
    
    return render_template('labeling.html', 
                         comic_id=comic_id,
                         comic_data=comic_data,
                         progress=progress,
                         current_index=current_index,
                         total_comics=len(labeling_app.comic_ids))

@app.route('/api/save_label', methods=['POST'])
def save_label():
    """API endpoint to save a label"""
    data = request.json
    comic_id = data.get('comic_id')
    selected = data.get('selected')
    custom_explanation = data.get('custom_explanation', '')
    
    if not comic_id or not selected:
        return jsonify({'error': 'Missing required fields'}), 400
    
    success = labeling_app.save_label(comic_id, selected, custom_explanation)
    if not success:
        return jsonify({'error': 'Failed to save label'}), 500
    
    # Get next comic
    next_comic = labeling_app.get_next_unlabeled(comic_id)
    
    return jsonify({
        'success': True,
        'next_comic': next_comic,
        'progress': labeling_app.get_progress()
    })

@app.route('/api/progress')
def get_progress():
    """API endpoint to get progress"""
    return jsonify(labeling_app.get_progress())

@app.route('/complete')
def complete():
    """Completion page"""
    return render_template('complete.html', progress=labeling_app.get_progress())

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True, host='127.0.0.1', port=5000)