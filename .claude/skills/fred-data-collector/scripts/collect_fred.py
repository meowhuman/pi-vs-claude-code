#!/usr/bin/env python3
"""
FRED Data Collector - Automated macroeconomic data collection
Federal Reserve Economic Data API client for Druckenmiller-style analysis
"""

# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "fredapi>=0.5.1",
#   "pandas>=1.5.0",
#   "requests>=2.28.0"
# ]
# ///

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from fredapi import Fred

# Load .env file
def load_env():
    """Load .env file from project root"""
    cwd = os.getcwd()
    env_file = os.path.join(cwd, '.env')

    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        os.environ[key] = value
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")

load_env()  # Load environment variables

# Configuration
DEFAULT_SERIES = {
    'economic': {
        'GDP': 'Real GDP',
        'CPIAUCSL': 'Consumer Price Index for All Urban Consumers',
        'UNRATE': 'Unemployment Rate',
        'PAYEMS': 'Nonfarm Payrolls',
        'ICSA': 'Initial Claims'
    },
    'rates': {
        'DFF': 'Federal Funds Effective Rate',
        'DGS2': '2-Year Treasury',
        'DGS10': '10-Year Treasury',
        'DGS30': '30-Year Treasury'
    },
    'money': {
        'M2SL': 'M2 Money Stock',
        'WALCL': 'Federal Reserve Balance Sheet'
    }
}

class FREDCollector:
    def __init__(self, api_key=None, data_dir=None):
        """Initialize FRED collector"""
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found. Set environment variable or pass api_key parameter.")

        self.fred = Fred(api_key=self.api_key)
        self.data_dir = Path(data_dir or os.getenv('FRED_DATA_DIR', './datas/fred'))
        self._ensure_directories()

        print(f"✓ FRED Collector initialized")
        print(f"  API Key: {self.api_key[:8]}...")
        print(f"  Data Directory: {self.data_dir.absolute()}")

    def _ensure_directories(self):
        """Create necessary directories"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / 'daily').mkdir(exist_ok=True)
        (self.data_dir / 'economic').mkdir(exist_ok=True)
        (self.data_dir / 'rates').mkdir(exist_ok=True)
        (self.data_dir / 'money').mkdir(exist_ok=True)
        (self.data_dir / 'summary').mkdir(exist_ok=True)

    def collect_series(self, series_id, name=None, category='other'):
        """Collect data for a specific FRED series"""
        try:
            print(f"  Fetching {series_id}...", end=" ")
            series = self.fred.get_series(series_id)

            if series.empty:
                print(f"✗ No data")
                return None

            # Save full history
            filename = self.data_dir / category / f'{series_id}_history.csv'
            series.to_csv(filename)

            # Get latest value
            latest_value = series.iloc[-1]
            latest_date = series.index[-1]

            print(f"✓ {latest_value} (as of {latest_date.strftime('%Y-%m-%d')})")

            return {
                'series_id': series_id,
                'name': name or series_id,
                'latest_value': latest_value,
                'latest_date': latest_date,
                'history': series,
                'filename': filename
            }

        except Exception as e:
            print(f"✗ Error: {e}")
            return None

    def collect_category(self, category):
        """Collect all series in a category"""
        if category not in DEFAULT_SERIES:
            print(f"Unknown category: {category}")
            return {}

        print(f"\n📊 Collecting {category.upper()} data...")
        results = {}

        for series_id, name in DEFAULT_SERIES[category].items():
            result = self.collect_series(series_id, name, category)
            if result:
                results[series_id] = result

        return results

    def collect_custom(self, series_ids):
        """Collect custom series IDs"""
        print(f"\n📊 Collecting custom series...")
        results = {}

        for series_id in series_ids:
            series_id = series_id.strip()
            if series_id:
                result = self.collect_series(series_id, series_id, 'custom')
                if result:
                    results[series_id] = result

        return results

    def generate_summary(self, all_data):
        """Generate markdown summary report"""
        print(f"\n📝 Generating summary report...")

        timestamp = datetime.now()
        report_file = self.data_dir / 'summary' / f'report_{timestamp.strftime("%Y%m%d_%H%M%S")}.md'

        with open(report_file, 'w') as f:
            f.write(f"# FRED Economic Data Summary\n\n")
            f.write(f"**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**API Key:** {self.api_key[:8]}...\n\n")

            for category, data in all_data.items():
                if data:
                    f.write(f"## {category.title()} Indicators\n\n")
                    f.write(f"| Indicator | Latest | Date | Series ID |\n")
                    f.write(f"|-----------|--------|------|-----------|\n")

                    for series_id, result in data.items():
                        if result:
                            f.write(f"| {result['name']} | {result['latest_value']:.2f} | {result['latest_date'].strftime('%Y-%m-%d')} | {series_id} |\n")

                    f.write(f"\n")

        print(f"✓ Report saved: {report_file}")
        return report_file

    def show_status(self):
        """Show API status and usage limits"""
        try:
            # Test connection
            test_series = self.fred.get_series('GDP', limit=1)
            print(f"✓ API Connection: OK")
            print(f"✓ Rate Limit: 120 requests/hour (free tier)")
            print(f"✓ Daily Limit: None")
            return True
        except Exception as e:
            print(f"✗ API Connection Failed: {e}")
            return False

def interactive_mode(collector):
    """Interactive collection mode"""
    print(f"\n{'='*60}")
    print("FRED Data Collector - Interactive Mode")
    print(f"{'='*60}\n")

    while True:
        print("Select data category to collect:")
        print("1. Economic Indicators (GDP, CPI, Unemployment)")
        print("2. Interest Rates (Fed Funds, Treasury yields)")
        print("3. Money Supply (M2, Fed Balance Sheet)")
        print("4. All Categories")
        print("5. Custom Series")
        print("6. Check API Status")
        print("0. Exit")

        choice = input(f"\nEnter choice (0-6): ").strip()

        if choice == '0':
            print("Goodbye!")
            break

        elif choice == '1':
            collector.collect_category('economic')

        elif choice == '2':
            collector.collect_category('rates')

        elif choice == '3':
            collector.collect_category('money')

        elif choice == '4':
            all_data = {}
            for category in DEFAULT_SERIES.keys():
                all_data[category] = collector.collect_category(category)
            collector.generate_summary(all_data)

        elif choice == '5':
            series_input = input("Enter series IDs (comma-separated): ")
            series_ids = [sid.strip() for sid in series_input.split(',')]
            collector.collect_custom(series_ids)

        elif choice == '6':
            collector.show_status()

        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='FRED Data Collector')
    parser.add_argument('--category', '-c', choices=['economic', 'rates', 'money', 'all'],
                       help='Collect specific category')
    parser.add_argument('--custom', nargs='+', help='Collect custom series IDs')
    parser.add_argument('--config', help='JSON config file with series list')
    parser.add_argument('--status', action='store_true', help='Check API status')
    parser.add_argument('--auto', action='store_true', help='Run in auto mode (collect all)')
    args = parser.parse_args()

    try:
        # Initialize collector
        collector = FREDCollector()

        # Handle command-line arguments
        if args.status:
            collector.show_status()
            return

        if args.auto:
            print("Running in auto mode (collecting all categories)...")
            all_data = {}
            for category in DEFAULT_SERIES.keys():
                all_data[category] = collector.collect_category(category)
            collector.generate_summary(all_data)
            return

        if args.category:
            if args.category == 'all':
                all_data = {}
                for category in DEFAULT_SERIES.keys():
                    all_data[category] = collector.collect_category(category)
                collector.generate_summary(all_data)
            else:
                collector.collect_category(args.category)
            return

        if args.custom:
            collector.collect_custom(args.custom)
            return

        if args.config:
            with open(args.config, 'r') as f:
                config = json.load(f)
            series_ids = config.get('series', [])
            collector.collect_custom(series_ids)
            return

        # No arguments = interactive mode
        interactive_mode(collector)

    except ValueError as e:
        print(f"Error: {e}")
        print(f"\nPlease set FRED_API_KEY environment variable:")
        print(f"export FRED_API_KEY='your_api_key_here'")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
