"""
HTML Report Generator for TraceTap

Generates beautiful, single-file HTML reports from captured traffic with:
- Visual timeline of requests
- Coverage summary (endpoints, methods, status codes)
- Request/response details
- Test generation preview
- Mobile-responsive design
- Zero external dependencies (embedded CSS/JS)
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class HTMLReportGenerator:
    """Generate beautiful HTML reports from captured traffic"""

    def __init__(self, capture_data: Dict[str, Any]):
        """
        Initialize HTML report generator

        Args:
            capture_data: Raw JSON capture data from TraceTap
        """
        self.data = capture_data
        self.requests = capture_data.get("requests", [])
        self.metadata = capture_data.get("metadata", {})

    def generate(self, output_path: str) -> bool:
        """
        Generate HTML report and save to file

        Args:
            output_path: Path to save HTML file

        Returns:
            True if successful, False otherwise
        """
        try:
            html_content = self._build_html()

            output_file = Path(output_path)
            output_file.write_text(html_content, encoding="utf-8")

            return True
        except Exception as e:
            print(f"Error generating HTML report: {e}")
            return False

    def _build_html(self) -> str:
        """Build complete HTML document"""
        stats = self._calculate_stats()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TraceTap Report - {self.metadata.get('session_name', 'API Capture')}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._build_header()}
        {self._build_summary(stats)}
        {self._build_timeline()}
        {self._build_request_details()}
        {self._build_footer()}
    </div>
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>"""

    def _build_header(self) -> str:
        """Build report header"""
        session_name = self.metadata.get("session_name", "API Capture")
        timestamp = self.metadata.get("timestamp", datetime.now().isoformat())

        return f"""
        <header class="header">
            <div class="logo">
                <h1>🎯 TraceTap Report</h1>
                <p class="subtitle">From Traffic to Tests in Minutes</p>
            </div>
            <div class="header-info">
                <div class="info-item">
                    <span class="label">Session:</span>
                    <span class="value">{session_name}</span>
                </div>
                <div class="info-item">
                    <span class="label">Generated:</span>
                    <span class="value">{timestamp}</span>
                </div>
            </div>
        </header>
        """

    def _calculate_stats(self) -> Dict[str, Any]:
        """Calculate statistics from captured requests"""
        stats = {
            "total_requests": len(self.requests),
            "endpoints": set(),
            "methods": defaultdict(int),
            "status_codes": defaultdict(int),
            "hosts": set(),
            "total_duration": 0,
            "avg_duration": 0,
        }

        for req in self.requests:
            # Parse URL
            url = req.get("url", "")
            parsed = urlparse(url)
            path = parsed.path or "/"

            stats["endpoints"].add(f"{req.get('method', 'GET')} {path}")
            stats["methods"][req.get("method", "GET")] += 1
            stats["status_codes"][req.get("status_code", 0)] += 1
            stats["hosts"].add(parsed.netloc)

            # Duration
            duration = req.get("duration_ms", 0)
            stats["total_duration"] += duration

        if stats["total_requests"] > 0:
            stats["avg_duration"] = stats["total_duration"] / stats["total_requests"]

        stats["unique_endpoints"] = len(stats["endpoints"])
        stats["unique_hosts"] = len(stats["hosts"])

        return stats

    def _build_summary(self, stats: Dict[str, Any]) -> str:
        """Build summary statistics section"""
        method_cards = ""
        for method, count in sorted(stats["methods"].items()):
            method_cards += f"""
            <div class="stat-card method-{method.lower()}">
                <div class="stat-label">{method}</div>
                <div class="stat-value">{count}</div>
            </div>
            """

        status_breakdown = ""
        for status, count in sorted(stats["status_codes"].items()):
            status_class = self._get_status_class(status)
            status_breakdown += f"""
            <div class="status-item status-{status_class}">
                <span class="status-code">{status}</span>
                <span class="status-count">{count} requests</span>
            </div>
            """

        return f"""
        <section class="summary">
            <h2>📊 Capture Summary</h2>

            <div class="stat-grid">
                <div class="stat-card primary">
                    <div class="stat-label">Total Requests</div>
                    <div class="stat-value">{stats['total_requests']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Unique Endpoints</div>
                    <div class="stat-value">{stats['unique_endpoints']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Unique Hosts</div>
                    <div class="stat-value">{stats['unique_hosts']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Avg Response Time</div>
                    <div class="stat-value">{stats['avg_duration']:.0f}ms</div>
                </div>
            </div>

            <div class="methods-section">
                <h3>HTTP Methods</h3>
                <div class="methods-grid">
                    {method_cards}
                </div>
            </div>

            <div class="status-section">
                <h3>Status Code Distribution</h3>
                <div class="status-list">
                    {status_breakdown}
                </div>
            </div>
        </section>
        """

    def _get_status_class(self, status_code: int) -> str:
        """Get CSS class for status code"""
        if 200 <= status_code < 300:
            return "success"
        elif 300 <= status_code < 400:
            return "redirect"
        elif 400 <= status_code < 500:
            return "client-error"
        elif 500 <= status_code < 600:
            return "server-error"
        return "unknown"

    def _build_timeline(self) -> str:
        """Build visual timeline of requests"""
        timeline_items = ""

        for i, req in enumerate(self.requests[:50]):  # Limit to first 50 for performance
            url = req.get("url", "")
            method = req.get("method", "GET")
            status = req.get("status_code", 0)
            duration = req.get("duration_ms", 0)
            timestamp = req.get("timestamp", "")

            status_class = self._get_status_class(status)

            timeline_items += f"""
            <div class="timeline-item" data-index="{i}">
                <div class="timeline-marker status-{status_class}"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="method method-{method.lower()}">{method}</span>
                        <span class="url">{url}</span>
                        <span class="status status-{status_class}">{status}</span>
                    </div>
                    <div class="timeline-meta">
                        <span class="duration">{duration:.0f}ms</span>
                        <span class="timestamp">{timestamp}</span>
                    </div>
                </div>
            </div>
            """

        return f"""
        <section class="timeline">
            <h2>📈 Request Timeline</h2>
            <div class="timeline-container">
                {timeline_items}
            </div>
        </section>
        """

    def _build_request_details(self) -> str:
        """Build detailed request/response section"""
        return """
        <section class="details">
            <h2>🔍 Request Details</h2>
            <p class="details-hint">Click any request in the timeline above to view full details here.</p>
            <div id="request-details" class="request-details-container">
                <p class="no-selection">No request selected. Click a request in the timeline to view details.</p>
            </div>
        </section>
        """

    def _build_footer(self) -> str:
        """Build report footer"""
        return """
        <footer class="footer">
            <p>Generated by <strong>TraceTap</strong> - From Traffic to Tests in Minutes</p>
            <p><a href="https://github.com/VassilisSoum/tracetap" target="_blank">github.com/VassilisSoum/tracetap</a></p>
        </footer>
        """

    def _get_css(self) -> str:
        """Get embedded CSS styles"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .header-info {
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 40px;
            flex-wrap: wrap;
        }

        .info-item {
            display: flex;
            gap: 10px;
        }

        .info-item .label {
            opacity: 0.8;
        }

        .info-item .value {
            font-weight: bold;
        }

        section {
            padding: 40px;
            border-bottom: 1px solid #eee;
        }

        section:last-child {
            border-bottom: none;
        }

        h2 {
            font-size: 1.8rem;
            margin-bottom: 30px;
            color: #667eea;
        }

        h3 {
            font-size: 1.3rem;
            margin: 30px 0 20px 0;
            color: #555;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .stat-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #e9ecef;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }

        .stat-card.primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
        }

        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
        }

        .methods-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
        }

        .method-get { border-left: 4px solid #28a745; }
        .method-post { border-left: 4px solid #007bff; }
        .method-put { border-left: 4px solid #ffc107; }
        .method-delete { border-left: 4px solid #dc3545; }
        .method-patch { border-left: 4px solid #17a2b8; }

        .status-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            border-radius: 6px;
            background: #f8f9fa;
        }

        .status-success { border-left: 4px solid #28a745; }
        .status-redirect { border-left: 4px solid #17a2b8; }
        .status-client-error { border-left: 4px solid #ffc107; }
        .status-server-error { border-left: 4px solid #dc3545; }

        .status-code {
            font-weight: bold;
            font-size: 1.1rem;
        }

        .timeline-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .timeline-item {
            display: flex;
            gap: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s, transform 0.2s;
        }

        .timeline-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }

        .timeline-marker {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-top: 6px;
            flex-shrink: 0;
        }

        .timeline-content {
            flex: 1;
        }

        .timeline-header {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        .method {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: bold;
            color: white;
        }

        .method-get { background: #28a745; }
        .method-post { background: #007bff; }
        .method-put { background: #ffc107; color: #333; }
        .method-delete { background: #dc3545; }
        .method-patch { background: #17a2b8; }

        .url {
            flex: 1;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }

        .status {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: bold;
        }

        .timeline-meta {
            margin-top: 8px;
            font-size: 0.85rem;
            color: #666;
            display: flex;
            gap: 20px;
        }

        .footer {
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
        }

        .footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }

        .footer a:hover {
            text-decoration: underline;
        }

        .no-selection {
            text-align: center;
            color: #999;
            padding: 60px 20px;
        }

        @media (max-width: 768px) {
            .container {
                border-radius: 0;
            }

            .header h1 {
                font-size: 1.8rem;
            }

            section {
                padding: 20px;
            }

            .stat-grid {
                grid-template-columns: 1fr;
            }

            .timeline-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
        }
        """

    def _get_javascript(self) -> str:
        """Get embedded JavaScript"""
        requests_json = json.dumps(self.requests)

        return f"""
        const requestsData = {requests_json};

        document.querySelectorAll('.timeline-item').forEach(item => {{
            item.addEventListener('click', () => {{
                const index = parseInt(item.dataset.index);
                showRequestDetails(requestsData[index]);
            }});
        }});

        function showRequestDetails(request) {{
            const container = document.getElementById('request-details');
            const headers = Object.entries(request.headers || {{}})
                .map(([key, value]) => `<div class="header-item"><strong>${{key}}:</strong> ${{value}}</div>`)
                .join('');

            const responseHeaders = Object.entries(request.response_headers || {{}})
                .map(([key, value]) => `<div class="header-item"><strong>${{key}}:</strong> ${{value}}</div>`)
                .join('');

            container.innerHTML = `
                <div style="padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h3 style="margin-top: 0;">${{request.method}} ${{request.url}}</h3>

                    <h4 style="margin-top: 30px;">Request Headers</h4>
                    <div style="font-family: monospace; font-size: 0.9rem; line-height: 1.8;">
                        ${{headers}}
                    </div>

                    ${{request.body ? `
                        <h4 style="margin-top: 20px;">Request Body</h4>
                        <pre style="background: white; padding: 15px; border-radius: 4px; overflow-x: auto;">${{JSON.stringify(JSON.parse(request.body), null, 2)}}</pre>
                    ` : ''}}

                    <h4 style="margin-top: 30px;">Response</h4>
                    <div style="margin-bottom: 10px;">
                        <span style="padding: 6px 12px; background: #28a745; color: white; border-radius: 4px; font-weight: bold;">
                            ${{request.status_code}}
                        </span>
                        <span style="margin-left: 15px; color: #666;">${{request.duration_ms}}ms</span>
                    </div>

                    <h4 style="margin-top: 20px;">Response Headers</h4>
                    <div style="font-family: monospace; font-size: 0.9rem; line-height: 1.8;">
                        ${{responseHeaders}}
                    </div>

                    ${{request.response_body ? `
                        <h4 style="margin-top: 20px;">Response Body</h4>
                        <pre style="background: white; padding: 15px; border-radius: 4px; overflow-x: auto; max-height: 400px;">${{JSON.stringify(JSON.parse(request.response_body), null, 2)}}</pre>
                    ` : ''}}
                </div>
            `;
        }}
        """


def generate_html_report(json_file: str, output_file: str) -> bool:
    """
    Generate HTML report from TraceTap JSON capture

    Args:
        json_file: Path to JSON capture file
        output_file: Path to save HTML report

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        generator = HTMLReportGenerator(data)
        return generator.generate(output_file)

    except FileNotFoundError:
        print(f"Error: File not found: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file}: {e}")
        return False
    except Exception as e:
        print(f"Error generating report: {e}")
        return False
