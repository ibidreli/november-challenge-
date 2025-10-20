#!/usr/bin/env python3
"""
Test script to demonstrate the Render database URL conversion fix.
Run this to verify the conversion logic works correctly.
"""

from urllib.parse import urlparse
import sys

def _convert_render_internal_to_external(url: str) -> str:
    """
    Convert Render internal database URLs to external URLs.
    
    Render provides both internal and external database URLs:
    - Internal: postgresql://user:pass@dpg-xxxxx-a/dbname (only works within Render)
    - External: postgresql://user:pass@dpg-xxxxx-a.oregon-postgres.render.com/dbname
    
    This function detects internal Render URLs and converts them to external ones.
    """
    try:
        p = urlparse(url)
        if p.scheme and p.scheme.startswith("postgres") and p.hostname:
            host = p.hostname
            if (host.startswith("dpg-") and host.endswith("-a") and 
                "render.com" not in host and "." not in host):
                external_host = f"{host}.oregon-postgres.render.com"
                
                auth = ""
                if p.username:
                    auth = p.username
                    if p.password:
                        auth += ":" + p.password
                    auth += "@"
                port_part = f":{p.port}" if p.port else ""
                external_url = f"{p.scheme}://{auth}{external_host}{port_part}{p.path}"
                
                return external_url
        return url
    except Exception as e:
        print(f"Error converting URL: {e}")
        return url

def mask_password(url: str) -> str:
    """Mask password in URL for display."""
    try:
        p = urlparse(url)
        if p.password:
            masked = url.replace(p.password, "***")
            return masked
        return url
    except:
        return url

def run_tests():
    """Run test cases to verify the conversion logic."""
    print("=" * 70)
    print("Testing Render Database URL Conversion")
    print("=" * 70)
    print()
    
    tests = [
        {
            "name": "Render Internal URL (should convert)",
            "input": "postgresql://admin:E9XMFQ4IIpA6NjTCiHHXuRw2YVN6WC5R@dpg-d3nnp7mr433s73bmb96g-a/novemberchallenge",
            "expected": "postgresql://admin:E9XMFQ4IIpA6NjTCiHHXuRw2YVN6WC5R@dpg-d3nnp7mr433s73bmb96g-a.oregon-postgres.render.com/novemberchallenge",
            "should_convert": True
        },
        {
            "name": "Render External URL (should NOT convert)",
            "input": "postgresql://user:pass@dpg-xyz-a.oregon-postgres.render.com/db",
            "expected": "postgresql://user:pass@dpg-xyz-a.oregon-postgres.render.com/db",
            "should_convert": False
        },
        {
            "name": "Localhost URL (should NOT convert)",
            "input": "postgresql://user:pass@localhost:5432/mydb",
            "expected": "postgresql://user:pass@localhost:5432/mydb",
            "should_convert": False
        },
        {
            "name": "AWS RDS URL (should NOT convert)",
            "input": "postgresql://user:pass@mydb.abc.us-east-1.rds.amazonaws.com/db",
            "expected": "postgresql://user:pass@mydb.abc.us-east-1.rds.amazonaws.com/db",
            "should_convert": False
        },
        {
            "name": "SQLite URL (should NOT convert)",
            "input": "sqlite:///./dev.db",
            "expected": "sqlite:///./dev.db",
            "should_convert": False
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(tests, 1):
        print(f"Test {i}: {test['name']}")
        print("-" * 70)
        print(f"  Input:    {mask_password(test['input'])}")
        
        result = _convert_render_internal_to_external(test['input'])
        print(f"  Output:   {mask_password(result)}")
        print(f"  Expected: {mask_password(test['expected'])}")
        
        if result == test['expected']:
            print("  Status:   ✓ PASS")
            passed += 1
        else:
            print("  Status:   ✗ FAIL")
            failed += 1
        print()
    
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
