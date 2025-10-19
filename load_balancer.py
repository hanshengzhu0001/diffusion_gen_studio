#!/usr/bin/env python3
"""
Enhanced Load Balancer for ML-MDM Horizontal Scaling Demo
Distributes requests across multiple instances with real-time monitoring
"""

import random
import requests
import time
import json
from flask import Flask, request, jsonify, redirect, render_template_string
import threading
from datetime import datetime

app = Flask(__name__)

# Available instances
INSTANCES = [
    "http://localhost:8080",
    "http://localhost:8081", 
    "http://localhost:8082"
]

# Round-robin counter
counter = 0

# Instance monitoring data
instance_stats = {
    inst: {
        "requests_served": 0,
        "last_request": None,
        "status": "unknown",
        "response_time": 0,
        "current_generation": None,
        "model_loaded": False,
        "cache_hits": 0
    }
    for inst in INSTANCES
}

# Model cache for faster startup
model_cache = {}

# HTML Dashboard Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ML-MDM Load Balancer Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 30px; 
            backdrop-filter: blur(10px);
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
        }
        .header h1 { 
            margin: 0; 
            font-size: 2.5em; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .stat-card { 
            background: rgba(255,255,255,0.15); 
            border-radius: 10px; 
            padding: 20px; 
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-number { 
            font-size: 2em; 
            font-weight: bold; 
            margin-bottom: 10px; 
        }
        .instance-card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 10px; 
            padding: 20px; 
            margin-bottom: 15px;
            border-left: 5px solid #4CAF50;
        }
        .instance-card.unhealthy { 
            border-left-color: #f44336; 
        }
        .instance-card.error { 
            border-left-color: #ff9800; 
        }
        .status { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
            text-transform: uppercase;
            font-size: 0.8em;
        }
        .status.healthy { 
            background: #4CAF50; 
            color: white; 
        }
        .status.unhealthy { 
            background: #f44336; 
            color: white; 
        }
        .status.error { 
            background: #ff9800; 
            color: white; 
        }
        .btn { 
            background: #4CAF50; 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 25px; 
            font-size: 1.1em; 
            cursor: pointer; 
            text-decoration: none;
            display: inline-block;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .btn:hover { 
            background: #45a049; 
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .refresh-info { 
            text-align: center; 
            margin-top: 20px; 
            opacity: 0.8; 
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            width: 0%;
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ML-MDM Load Balancer</h1>
            <p>Real-time Horizontal Scaling Dashboard</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-requests">0</div>
                <div>Total Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="healthy-instances">0</div>
                <div>Healthy Instances</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="current-time">--:--:--</div>
                <div>Last Update</div>
            </div>
        </div>
        
        <div id="instances-container">
            <!-- Instances will be populated here -->
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/redirect" class="btn">🎨 Generate Images</a>
            <a href="/health" class="btn">📊 Health Check</a>
            <a href="/stats" class="btn">📈 Statistics</a>
        </div>
        
        <div class="refresh-info">
            <p>🔄 Auto-refreshing every 2 seconds</p>
        </div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('total-requests').textContent = data.total_requests;
                    document.getElementById('healthy-instances').textContent = data.healthy_instances;
                    document.getElementById('current-time').textContent = data.timestamp;
                    
                    const container = document.getElementById('instances-container');
                    container.innerHTML = '';
                    
                    data.instances.forEach(instance => {
                        const card = document.createElement('div');
                        card.className = `instance-card ${instance.status}`;
                        
                        const statusClass = instance.status === 'healthy' ? 'healthy' : 
                                          instance.status === 'unhealthy' ? 'unhealthy' : 'error';
                        
                        card.innerHTML = `
                            <h3>Instance ${instance.port}</h3>
                            <div style="margin: 10px 0;">
                                <span class="status ${statusClass}">${instance.status}</span>
                                <span style="margin-left: 15px;">Response: ${instance.response_time}</span>
                                <span style="margin-left: 15px; color: ${instance.model_loaded ? '#4CAF50' : '#ff9800'};">
                                    Model: ${instance.model_loaded ? 'Loaded' : 'Loading...'}
                                </span>
                            </div>
                            <div style="margin: 10px 0;">
                                <strong>Requests Served:</strong> ${instance.requests_served}
                                <span style="margin-left: 20px;"><strong>Last Request:</strong> ${instance.last_request || 'Never'}</span>
                                <span style="margin-left: 20px;"><strong>Cache Hits:</strong> ${instance.cache_hits || 0}</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${Math.min(instance.requests_served * 10, 100)}%"></div>
                            </div>
                        `;
                        
                        container.appendChild(card);
                    });
                })
                .catch(error => {
                    console.error('Error updating dashboard:', error);
                });
        }
        
        // Update immediately and then every 2 seconds
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

def get_next_instance():
    """Get next instance using round-robin"""
    global counter
    instance = INSTANCES[counter % len(INSTANCES)]
    counter += 1
    return instance

def get_random_instance():
    """Get random instance"""
    return random.choice(INSTANCES)

def check_instance_health(instance_url):
    """Check if instance is healthy and update stats"""
    try:
        start_time = time.time()
        response = requests.get(f"{instance_url}/", timeout=5)
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            instance_stats[instance_url]["status"] = "healthy"
            instance_stats[instance_url]["response_time"] = response_time
            
            # Check if model is loaded by looking for specific content
            if "ML-MDM" in response.text or "Gradio" in response.text:
                instance_stats[instance_url]["model_loaded"] = True
                model_cache[instance_url] = True
            else:
                instance_stats[instance_url]["model_loaded"] = False
                
            return True
        else:
            instance_stats[instance_url]["status"] = "unhealthy"
            return False
    except Exception as e:
        instance_stats[instance_url]["status"] = "error"
        instance_stats[instance_url]["response_time"] = 0
        return False

def update_instance_stats(instance_url, request_type="generation"):
    """Update instance statistics"""
    instance_stats[instance_url]["requests_served"] += 1
    instance_stats[instance_url]["last_request"] = datetime.now().strftime("%H:%M:%S")
    instance_stats[instance_url]["current_generation"] = request_type

@app.route('/')
def home():
    """Show monitoring dashboard"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/redirect')
def redirect_to_instance():
    """Redirect to a healthy instance"""
    healthy_instances = [inst for inst in INSTANCES if check_instance_health(inst)]
    
    if not healthy_instances:
        return "No healthy instances available", 503
    
    # Use round-robin for load balancing
    instance = get_next_instance()
    
    # If the selected instance is not healthy, pick a random healthy one
    if not check_instance_health(instance):
        instance = random.choice(healthy_instances)
    
    # Update stats for the selected instance
    update_instance_stats(instance)
    
    return redirect(f"{instance}/", code=302)

@app.route('/health')
def health():
    """Health check endpoint"""
    healthy_count = sum(1 for inst in INSTANCES if check_instance_health(inst))
    return jsonify({
        "status": "healthy" if healthy_count > 0 else "unhealthy",
        "healthy_instances": healthy_count,
        "total_instances": len(INSTANCES),
        "instances": [
            {
                "url": inst,
                "healthy": check_instance_health(inst)
            }
            for inst in INSTANCES
        ]
    })

@app.route('/stats')
def stats():
    """Get load balancer statistics"""
    return jsonify({
        "load_balancer": "ML-MDM Horizontal Scaling Demo",
        "strategy": "Round-robin with health checks",
        "instances": INSTANCES,
        "current_counter": counter,
        "instance_stats": instance_stats
    })

@app.route('/api/status')
def api_status():
    """API endpoint for real-time status updates"""
    # Update health for all instances
    for inst in INSTANCES:
        check_instance_health(inst)
    
    return jsonify({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "total_requests": sum(stats["requests_served"] for stats in instance_stats.values()),
        "healthy_instances": sum(1 for inst in INSTANCES if check_instance_health(inst)),
        "instances": [
            {
                "url": inst,
                "port": inst.split(":")[-1],
                "status": instance_stats[inst]["status"],
                "requests_served": instance_stats[inst]["requests_served"],
                "last_request": instance_stats[inst]["last_request"],
                "response_time": f"{instance_stats[inst]['response_time']:.1f}ms",
                "current_generation": instance_stats[inst]["current_generation"],
                "model_loaded": instance_stats[inst]["model_loaded"],
                "cache_hits": instance_stats[inst]["cache_hits"]
            }
            for inst in INSTANCES
        ]
    })

if __name__ == '__main__':
    print("🚀 ML-MDM Load Balancer Starting...")
    print(f"📊 Managing {len(INSTANCES)} instances:")
    for i, inst in enumerate(INSTANCES, 1):
        print(f"   Instance {i}: {inst}")
    print("\n🌐 Load Balancer: http://localhost:5000")
    print("📈 Health Check: http://localhost:5000/health")
    print("📊 Statistics: http://localhost:5000/stats")
    print("\n⚖️ Load balancing strategy: Round-robin with health checks")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
