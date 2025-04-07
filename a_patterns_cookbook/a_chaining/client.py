import httpx

data_processing_steps = [
    """Extract only the numerical values and their associated metrics from the text.
    Format each as 'value: metric' on a new line.
    Example format:
    92: customer satisfaction
    45%: revenue growth""",
    """Convert all numerical values to percentages where possible.
    If not a percentage or points, convert to decimal (e.g., 92 points -> 92%).
    Keep one number per line.
    Example format:
    92%: customer satisfaction
    45%: revenue growth""",
    """Sort all lines in descending order by numerical value.
    Keep the format 'value: metric' on each line.
    Example:
    92%: customer satisfaction
    87%: employee satisfaction""",
    """Format the sorted data as a markdown table with columns:
    | Metric | Value |
    |:--|--:|
    | Customer Satisfaction | 92% |""",
]

report = """
Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%.
New user acquisition cost is $43 per user.
Product adoption rate increased to 78%.
Employee satisfaction is at 87 points.
Operating margin improved to 34%.
"""

data = {"input": report, "prompts": data_processing_steps}


headers = {"Content-Type": "application/json", "Accept": "application/json"}

r = httpx.post(
    "http://localhost:8080/CallChainingService/chain_call",
    json=data,
    headers=headers,
    timeout=60,
)

print(r.json())

"""
The service logs show an output similar to:

Step 1:
92: customer satisfaction  
45%: revenue growth  
23%: market share  
5%: customer churn  
43: new user acquisition cost  
78%: product adoption rate  
87: employee satisfaction  
34%: operating margin  

Step 2:
92%: customer satisfaction  
45%: revenue growth  
23%: market share  
5%: customer churn  
43%: new user acquisition cost  
78%: product adoption rate  
87%: employee satisfaction  
34%: operating margin  

Step 3:
Here is the sorted list in descending order by numerical value:

```
92%: customer satisfaction
87%: employee satisfaction
78%: product adoption rate
45%: revenue growth
43%: new user acquisition cost
34%: operating margin
23%: market share
5%: customer churn
```

Step 4:
Here is the sorted data formatted as a markdown table:

```markdown
| Metric                     | Value |
|:---------------------------|------:|
| Customer Satisfaction      |   92% |
| Employee Satisfaction      |   87% |
| Product Adoption Rate      |   78% |
| Revenue Growth             |   45% |
| New User Acquisition Cost  |   43% |
| Operating Margin           |   34% |
| Market Share               |   23% |
| Customer Churn             |    5% |
```
"""
