import json
import os
import argparse

def insert_newlines(string, every=15):
    """Helper to break long strings into multiple lines"""
    if not string:
        return ""
    return '\n'.join(string[i:i+every] for i in range(0, len(string), every))

def generate_html(input_file="data/pipeline_results.jsonl", output_file="data/graph.html"):
    if not os.path.exists(input_file):
        print(f"[Error] Input file {input_file} not found. Please run main.py first.")
        return
        
    nodes = []
    edges = []
    entity_set = set()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            article_id = data.get('article_id')
            article_title = data.get('article_title', article_id)
            summary = data.get('summary', '')
            
            # Create node for the article, use formatted title for label
            nodes.append({
                "id": article_id, 
                "label": insert_newlines(article_title, 15), 
                "group": "article", 
                "title": f"Summary: {summary}"  # Tooltip
            })
            
            # Support both old format (list of strings) and new format (list of dicts)
            linked_entities = data.get('linked_entities', [])
            for ent in linked_entities:
                if isinstance(ent, dict):
                    ent_name = ent.get("name")
                    ent_type = ent.get("type", "conservative")
                else:
                    ent_name = ent
                    ent_type = "conservative"
                    
                if not ent_name:
                    continue
                    
                if ent_name not in entity_set:
                    nodes.append({
                        "id": ent_name, 
                        "label": insert_newlines(ent_name, 12), 
                        "group": "entity_conservative" if ent_type == "conservative" else "entity_granular",
                        "title": ent_name
                    })
                    entity_set.add(ent_name)
                
                # Edge from article to entity
                edges.append({
                    "from": article_id, 
                    "to": ent_name
                })
                
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)
                
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>LLM Wikidata Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body, html {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: Arial, sans-serif;
        }}
        #mynetwork {{
            width: 100%;
            height: 100%;
            background-color: #f8f9fa;
        }}
        #info {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            z-index: 10;
        }}
    </style>
</head>
<body>
<div id="info">
    <h3>LLM Wikidata</h3>
    <p>🔵 <b>Articles</b> (Hover to view summary)</p>
    <p>🟢 <b>Conservative Entities</b> (Stable / Broad Concepts)</p>
    <p>🟠 <b>Granular Entities</b> (Specific / Detailed Concepts)</p>
</div>
<div id="mynetwork"></div>

<script type="text/javascript">
    var nodes = new vis.DataSet({nodes_json});
    var edges = new vis.DataSet({edges_json});
    
    var container = document.getElementById('mynetwork');
    var data = {{
        nodes: nodes,
        edges: edges
    }};
    var options = {{
        nodes: {{
            shape: 'dot',
            size: 20,
            font: {{
                size: 14,
                color: '#333'
            }},
            borderWidth: 2
        }},
        edges: {{
            width: 1.5,
            color: {{ inherit: 'from' }},
            smooth: {{
                type: 'continuous'
            }}
        }},
        groups: {{
            article: {{
                color: {{ background: '#97C2FC', border: '#2B7CE9' }},
                shape: 'box',
                font: {{ size: 14, color: '#000', bold: true }}
            }},
            entity_conservative: {{
                color: {{ background: '#7BE141', border: '#41A906' }},
                shape: 'ellipse',
                font: {{ size: 12, color: '#000' }}
            }},
            entity_granular: {{
                color: {{ background: '#FFA807', border: '#D98900' }},
                shape: 'ellipse',
                font: {{ size: 12, color: '#000' }}
            }}
        }},
        physics: {{
            enabled: true,
            forceAtlas2Based: {{
                gravitationalConstant: -100,
                centralGravity: 0.01,
                springLength: 150,
                springConstant: 0.08
            }},
            maxVelocity: 50,
            solver: 'forceAtlas2Based',
            timestep: 0.35,
            stabilization: {{ 
                enabled: true,
                iterations: 200,
                updateInterval: 25,
                onlyDynamicEdges: false,
                fit: true
            }}
        }},
        layout: {{
            randomSeed: 42
        }},
        interaction: {{
            hover: true,
            tooltipDelay: 200
        }}
    }};
    var network = new vis.Network(container, data, options);
    
    // Stop physics after initial stabilization to prevent continuous rotation/jiggling
    network.on("stabilizationIterationsDone", function () {{
        network.setOptions( {{ physics: false }} );
    }});
</script>
</body>
</html>
"""
    
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"--- Visualization Generated ---")
    print(f"Nodes: {len(nodes)} (Articles: {len(nodes) - len(entity_set)}, Entities: {len(entity_set)})")
    print(f"Edges: {len(edges)}")
    print(f"Saved to: {output_file}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an HTML visualization of the LLM Wikidata")
    parser.add_argument("--input", type=str, default="data/pipeline_results.jsonl", help="Input JSONL file")
    parser.add_argument("--output", type=str, default="data/graph.html", help="Output HTML file")
    
    args = parser.parse_args()
    generate_html(args.input, args.output)