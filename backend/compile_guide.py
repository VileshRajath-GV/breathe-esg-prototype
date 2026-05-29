import os
import re
import markdown

# Paths of all files to merge
FILES = {
    "1. Implementation Plan": r"C:\Users\adhes\.gemini\antigravity\brain\1bd74fe2-dd68-40f0-a685-1b1355548173\implementation_plan.md",
    "2. Walkthrough": r"C:\Users\adhes\.gemini\antigravity\brain\1bd74fe2-dd68-40f0-a685-1b1355548173\walkthrough.md",
    "3. Database Models (MODEL.md)": r"c:\Users\adhes\OneDrive\Desktop\breathe_esg_prototype\breathe_esg_prototype\MODEL.md",
    "4. Architectural Decisions (DECISIONS.md)": r"c:\Users\adhes\OneDrive\Desktop\breathe_esg_prototype\breathe_esg_prototype\DECISIONS.md",
    "5. Research & Sample Data (SOURCES.md)": r"c:\Users\adhes\OneDrive\Desktop\breathe_esg_prototype\breathe_esg_prototype\SOURCES.md",
    "6. Exclusions & Scope (TRADEOFFS.md)": r"c:\Users\adhes\OneDrive\Desktop\breathe_esg_prototype\breathe_esg_prototype\TRADEOFFS.md",
}

OUTPUT_PATH = r"c:\Users\adhes\OneDrive\Desktop\breathe_esg_prototype\breathe_esg_prototype\Breathe_ESG_Complete_Project_Guide.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Breathe ESG - Complete Project Guide & Documentation</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #059669;
            --primary-light: #ecfdf5;
            --secondary: #0284c7;
            --secondary-light: #f0f9ff;
            --text-dark: #0f172a;
            --text-gray: #475569;
            --bg-light: #f8fafc;
            --border-color: #e2e8f0;
            --scope1: #f97316;
            --scope2: #3b82f6;
            --scope3: #ef4444;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            color: var(--text-dark);
            background-color: var(--bg-light);
            line-height: 1.6;
            font-size: 15px;
            padding: 40px 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 24px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.03);
            padding: 50px;
        }}

        /* Header Styling */
        .header {{
            text-align: center;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 30px;
            margin-bottom: 40px;
        }}

        .header h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 38px;
            font-weight: 900;
            color: var(--text-dark);
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 16px;
            color: var(--text-gray);
            font-weight: 500;
        }}

        .header .meta {{
            margin-top: 15px;
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 6px 16px;
            background-color: var(--primary-light);
            color: var(--primary);
            border-radius: 100px;
        }}

        /* Table of Contents */
        .toc {{
            background: var(--bg-light);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 50px;
        }}

        .toc h3 {{
            font-family: 'Outfit', sans-serif;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 15px;
            color: var(--text-dark);
        }}

        .toc ul {{
            list-style: none;
        }}

        .toc li {{
            margin-bottom: 8px;
        }}

        .toc a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: color 0.2s;
        }}

        .toc a:hover {{
            color: var(--secondary);
            text-decoration: underline;
        }}

        /* Chapter Sections */
        .section-block {{
            margin-bottom: 60px;
            padding-bottom: 40px;
            border-bottom: 1px dashed var(--border-color);
        }}

        .section-block:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}

        /* Typography Inside Markdown Output */
        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 24px;
            font-weight: 800;
            margin: 30px 0 15px 0;
            color: var(--text-dark);
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 8px;
        }}

        h3 {{
            font-family: 'Outfit', sans-serif;
            font-size: 18px;
            font-weight: 700;
            margin: 25px 0 10px 0;
            color: var(--text-dark);
        }}

        h4 {{
            font-family: 'Outfit', sans-serif;
            font-size: 15px;
            font-weight: 700;
            margin: 20px 0 8px 0;
            color: var(--text-dark);
        }}

        p {{
            margin-bottom: 15px;
            color: var(--text-gray);
            font-size: 14.5px;
        }}

        ul, ol {{
            margin-bottom: 20px;
            padding-left: 20px;
            color: var(--text-gray);
        }}

        li {{
            margin-bottom: 6px;
            font-size: 14px;
        }}

        strong {{
            color: var(--text-dark);
            font-weight: 600;
        }}

        /* Code Blocks */
        pre {{
            background: #0f172a;
            color: #38bdf8;
            padding: 16px;
            border-radius: 12px;
            overflow-x: auto;
            margin: 20px 0;
            font-family: 'Courier New', Courier, monospace;
            font-size: 13px;
            border: 1px solid #1e293b;
        }}

        code {{
            font-family: 'Courier New', Courier, monospace;
            background: #f1f5f9;
            color: #0f172a;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
        }}

        pre code {{
            background: none;
            color: inherit;
            padding: 0;
            font-weight: normal;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 13.5px;
        }}

        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background-color: var(--bg-light);
            color: var(--text-dark);
            font-weight: 700;
        }}

        tr:hover td {{
            background-color: #f8fafc;
        }}

        /* Blockquotes / Custom Alerts */
        blockquote {{
            border-left: 4px solid var(--primary);
            background-color: var(--primary-light);
            padding: 15px 20px;
            border-radius: 0 12px 12px 0;
            margin: 20px 0;
        }}

        blockquote p {{
            margin-bottom: 0;
            color: var(--primary);
            font-weight: 500;
        }}

        /* Print Settings for PDF Generation */
        @media print {{
            body {{
                padding: 0;
                background-color: #ffffff;
            }}
            .container {{
                border: none;
                box-shadow: none;
                padding: 0;
            }}
            .section-block {{
                page-break-before: always;
            }}
            .toc {{
                display: none; /* Hide TOC on printed PDF for cleaner booklet feel */
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Breathe ESG Prototype</h1>
            <p>Comprehensive Implementation Report, Engineering Architecture & Verification Guide</p>
            <div class="meta">Breathe ESG Tech Intern Submission</div>
        </div>

        <div class="toc">
            <h3>Table of Contents</h3>
            <ul>
                {toc_items}
            </ul>
        </div>

        {sections_content}
    </div>
</body>
</html>
"""

def generate_guide():
    print("Compiling COMPLETE_PROJECT_GUIDE.html...")
    
    toc_items = ""
    sections_content = ""
    
    # Initialize Markdown Converter
    md = markdown.Markdown(extensions=['fenced_code', 'tables'])
    
    for idx, (title, filepath) in enumerate(FILES.items()):
        section_id = f"section_{idx}"
        
        # Add to TOC
        toc_items += f'<li><a href="#{section_id}">{title}</a></li>\n'
        
        # Read file
        if not os.path.exists(filepath):
            print(f"WARNING: File {filepath} not found. Skipping.")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Clean markdown elements if required (like custom carousel notations or raw absolute file links)
        # e.g. replacing file:/// links with relative descriptions for clean HTML print
        content = re.sub(r'file:///c:/[^\s\)]+', 'Local Workspace File', content)
        
        # Render markdown to HTML
        html_content = md.convert(content)
        
        # Wrap in section block
        sections_content += f"""
        <div id="{section_id}" class="section-block">
            {html_content}
        </div>
        """
        
    # Build complete HTML
    complete_html = HTML_TEMPLATE.format(
        toc_items=toc_items,
        sections_content=sections_content
    )
    
    # Write output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(complete_html)
        
    print(f"HTML compilation complete! Guide saved at: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_guide()
