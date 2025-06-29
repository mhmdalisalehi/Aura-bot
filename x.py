
import re
from pprint import pprint

with open('logs/workout_plan_generator.log', encoding='utf-8') as f:
    data = f.read()

# Replace 'namespace' with 'dict' for easier parsing
data = re.sub(r'namespace\(', 'dict(', data)
data = re.sub(r'\),', '),\n', data)  # Newline after each item

# Print the result
print(data)