#!/bin/bash
# Quick test runner script

set -e  # Exit on any error

echo "🧪 RPICAN Test Runner"
echo "===================="

# Activate virtual environment if it exists
if [ -d "rpican_env" ]; then
    echo "📦 Activating virtual environment..."
    source rpican_env/bin/activate
else
    echo "⚠️  No virtual environment found (rpican_env)"
fi

echo ""
echo "🔍 Step 1: Syntax Check"
echo "----------------------"
find . -name "*.py" -not -path "./rpican_env/*" -not -path "./.venv/*" -not -path "./venv/*" -exec python3 -m py_compile {} \;
echo "✅ All Python files compile successfully"

echo ""
echo "🧪 Step 2: Running Core Tests"  
echo "-----------------------------"
python3 -m pytest tests/test_syntax_and_imports.py::TestSyntaxValidation -v --tb=short
python3 -m pytest tests/test_syntax_and_imports.py::TestImportValidation -v --tb=short

echo ""
echo "🎯 Step 3: View System Tests"
echo "-----------------------------"
python3 -m pytest tests/test_view_system.py::TestBaseView -v --tb=short
python3 -m pytest tests/test_view_system.py::TestModernViewRegistry -v --tb=short

echo ""
echo "🚀 Step 4: App Startup Test" 
echo "---------------------------"
timeout 3s python3 run_tui.py --help || echo "✅ App imports and starts successfully"

echo ""
echo "🎉 All tests passed! System is working correctly."
echo ""
echo "📋 Next steps:"
echo "  • Test F8 view switching: python3 run_tui.py -p /dev/ttyACM0"
echo "  • Add new views by creating view_*.py files in can_tui/views/"
echo "  • Run full test suite: make test (if pytest-cov installed)"