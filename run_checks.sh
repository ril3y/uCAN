#!/bin/bash
# uCAN Firmware Quality Checks
# Run this before committing changes

set -e  # Exit on error

echo "=================================="
echo "uCAN Firmware Quality Checks"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Build both platforms
echo "1. Building firmware for all platforms..."
echo ""

echo "Building RP2040 (Pico)..."
pio run -e pico
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ RP2040 build successful${NC}"
else
    echo -e "${RED}✗ RP2040 build failed${NC}"
    exit 1
fi
echo ""

echo "Building SAMD51 (Feather M4 CAN)..."
pio run -e feather_m4_can
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SAMD51 build successful${NC}"
else
    echo -e "${RED}✗ SAMD51 build failed${NC}"
    exit 1
fi
echo ""

# 2. Run cppcheck for dead code analysis
echo "2. Running cppcheck for dead code analysis..."
echo ""

CPPCHECK_PATH="$HOME/.platformio/packages/tool-cppcheck/cppcheck"
if [ ! -f "$CPPCHECK_PATH" ]; then
    CPPCHECK_PATH="$HOME/.platformio/packages/tool-cppcheck/cppcheck.exe"
fi

if [ -f "$CPPCHECK_PATH" ]; then
    "$CPPCHECK_PATH" --enable=unusedFunction --quiet src/actions/ src/capabilities/ src/hal/ > cppcheck_report.txt 2>&1
    UNUSED_COUNT=$(wc -l < cppcheck_report.txt)
    
    if [ $UNUSED_COUNT -eq 0 ]; then
        echo -e "${GREEN}✓ No unused functions found${NC}"
    else
        echo -e "${YELLOW}⚠ Found $UNUSED_COUNT potentially unused functions${NC}"
        echo "  (See cppcheck_report.txt for details)"
        echo "  Note: Many are false positives (API functions, cross-file calls)"
    fi
else
    echo -e "${YELLOW}⚠ cppcheck not found, skipping${NC}"
fi
echo ""

# 3. Check for backup/temp files
echo "3. Checking for backup and temporary files..."
echo ""

BACKUP_FILES=$(find src -name "*.bak" -o -name "*~" -o -name "*.orig" 2>/dev/null)
if [ -z "$BACKUP_FILES" ]; then
    echo -e "${GREEN}✓ No backup files found${NC}"
else
    echo -e "${RED}✗ Found backup files:${NC}"
    echo "$BACKUP_FILES"
    exit 1
fi
echo ""

# 4. Summary
echo "=================================="
echo "Quality Check Summary"
echo "=================================="
echo -e "${GREEN}✓ All builds successful${NC}"
echo -e "${GREEN}✓ Static analysis complete${NC}"
echo -e "${GREEN}✓ No backup files${NC}"
echo ""
echo "Firmware is ready for commit!"
echo ""

