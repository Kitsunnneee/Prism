#!/bin/bash

# Simulate interactive menu input
# Option 1: Analyze
# Domain: devrev.ai
# Sample: 5
# Insights: yes
# Verbose: yes

echo "Testing interactive menu with DevRev analysis..."
echo ""

# Use printf to send inputs line by line
printf "1\ndevrev.ai\n5\ny\ny\ny\n" | python3 -m prism
