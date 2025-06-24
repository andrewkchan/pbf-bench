#!/usr/bin/env python3
import os
import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

def parse_comic_links(html_file):
    """Parse all comic links from the sample.html file using regex"""
    print(f"Parsing comic links from {html_file}...")
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all links with class="not_current_thumb" and their href values
    pattern = r'<a[^>]+class="not_current_thumb"[^>]+href="([^"]+)"'
    links = re.findall(pattern, content)
    
    print(f"Found {len(links)} comic links")
    return links

def extract_comic_info(html, url):
    """Extract comic image URL and metadata from comic page HTML using regex"""
    # Find the comic div and extract the image
    comic_div_pattern = r'<div[^>]+id="comic"[^>]*>(.*?)</div>'
    comic_match = re.search(comic_div_pattern, html, re.DOTALL)
    
    if not comic_match:
        print(f"Could not find comic div in {url}")
        return None
    
    comic_content = comic_match.group(1)
    
    # Extract image attributes
    img_pattern = r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\'][^>]*>'
    img_match = re.search(img_pattern, comic_content)
    
    if not img_match:
        print(f"Could not find image in comic div for {url}")
        return None
    
    img_url = img_match.group(1)
    
    # Skip placeholder images
    if img_url == "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==":
        # Try to find data-src instead
        data_src_pattern = r'data-src=["\']([^"\']+)["\']'
        data_src_match = re.search(data_src_pattern, comic_content)
        if data_src_match:
            img_url = data_src_match.group(1)
        else:
            print(f"Could not find valid image URL for {url}")
            return None
    
    # Extract other attributes
    alt_match = re.search(r'alt=["\']([^"\']*)["\']', comic_content)
    title_match = re.search(r'title=["\']([^"\']*)["\']', comic_content)
    width_match = re.search(r'width=["\']([^"\']*)["\']', comic_content)
    height_match = re.search(r'height=["\']([^"\']*)["\']', comic_content)
    
    # Extract metadata
    metadata = {
        'page_url': url,
        'image_url': img_url,
        'alt_text': alt_match.group(1) if alt_match else '',
        'title': title_match.group(1) if title_match else '',
        'width': width_match.group(1) if width_match else '',
        'height': height_match.group(1) if height_match else ''
    }
    
    # Try to extract comic title from the page
    title_pattern = r'<h1[^>]+class="pbf-comic-title"[^>]*>([^<]+)</h1>'
    title_elem_match = re.search(title_pattern, html)
    if title_elem_match:
        metadata['comic_title'] = title_elem_match.group(1).strip()
    
    # Extract filename from URL
    parsed_url = urllib.parse.urlparse(img_url)
    filename = os.path.basename(parsed_url.path)
    metadata['filename'] = filename
    
    return metadata

def download_file(url, output_path):
    """Download a file using urllib"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main():
    # Configuration
    sample_file = 'sample.html'
    output_dir = 'pbf_comics'
    metadata_file = 'pbf_comics_metadata.json'
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Parse comic links
    comic_links = parse_comic_links(sample_file)
    
    # Process each comic
    all_metadata = []
    
    for i, comic_url in enumerate(comic_links, 1):
        print(f"\nProcessing comic {i}/{len(comic_links)}: {comic_url}")
        
        # Download comic page
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            request = urllib.request.Request(comic_url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            print(f"Error downloading {comic_url}: {e}")
            continue
        
        # Extract comic info
        comic_info = extract_comic_info(html, comic_url)
        if not comic_info:
            continue
        
        # Download image
        image_path = os.path.join(output_dir, comic_info['filename'])
        if download_file(comic_info['image_url'], image_path):
            print(f"  Downloaded: {comic_info['filename']}")
            comic_info['local_path'] = image_path
            all_metadata.append(comic_info)
        
        # Be nice to the server
        time.sleep(0.5)
    
    # Save metadata
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\nDownload complete!")
    print(f"Downloaded {len(all_metadata)} comics to '{output_dir}'")
    print(f"Metadata saved to '{metadata_file}'")

if __name__ == "__main__":
    main()