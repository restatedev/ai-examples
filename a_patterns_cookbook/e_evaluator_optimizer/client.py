from pprint import pprint

import httpx

evaluator_prompt = """
Evaluate this following code implementation for:
1. code correctness
2. time complexity
3. style and best practices

You should be evaluating only and not attemping to solve the task.
Only output "PASS" if all criteria are met and you have no further suggestions for improvements.
Output your evaluation concisely in the following format.

<evaluation>PASS, NEEDS_IMPROVEMENT, or FAIL</evaluation>
<feedback>
What needs improvement and why.
</feedback>
"""

generator_prompt = """
Your goal is to complete the task based on <user input>. If there are feedback 
from your previous generations, you should reflect on them to improve your solution

Output your answer concisely in the following format: 

<thoughts>
[Your understanding of the task and feedback and how you plan to improve]
</thoughts>

<response>
[Your code implementation here]
</response>
"""

task = """
<user input>
Implement a Stack with:
1. push(x)
2. pop()
3. getMin()
All operations should be O(1).
</user input>
"""



data = {"task": task, "evaluator_prompt": evaluator_prompt, "generator_prompt": generator_prompt}


headers = {"Content-Type": "application/json", "Accept": "application/json"}

r = httpx.post(
    "http://localhost:8080/EvaluatorOptimizer/loop",
    json=data,
    headers=headers,
    timeout=60,
)

print("\nResult:")
print("-"*40)
print(r.json()[0])
print("\nChain of thought:")
print("-"*40)
pprint(r.json()[1])


"""
Service logs:

=== GENERATION START ===
Thoughts:

The task requires implementing a stack with three operations: push, pop, and getMin, all in constant time complexity, O(1). A common approach to achieve this is by using two stacks: one for storing the actual stack elements and another for keeping track of the minimum elements. This ensures that each operation can be performed in constant time. There is no feedback to consider, so I will proceed with this approach.


Generated:

```python
class MinStack:
    def __init__(self):
        self.stack = []
        self.min_stack = []

    def push(self, x):
        self.stack.append(x)
        # Push the new minimum onto the min_stack
        if not self.min_stack or x <= self.min_stack[-1]:
            self.min_stack.append(x)

    def pop(self):
        if self.stack:
            top = self.stack.pop()
            # If the popped element is the minimum, pop it from the min_stack as well
            if top == self.min_stack[-1]:
                self.min_stack.pop()

    def getMin(self):
        # The current minimum is the top of the min_stack
        if self.min_stack:
            return self.min_stack[-1]
        return None
```

=== GENERATION END ===

=== EVALUATION START ===
Status: PASS
Feedback: 
The code correctly implements a stack with push, pop, and getMin operations, all in O(1) time complexity. The use of an auxiliary stack (`min_stack`) to keep track of the minimum values ensures that the getMin operation is efficient. The code follows good style and best practices, with clear method names and appropriate use of data structures. No improvements are necessary.

=== EVALUATION END ===


=== GENERATION START ===
Thoughts:

The task requires implementing a stack that supports push, pop, and getMin operations, all in constant time complexity, O(1). A common approach to achieve this is by using two stacks: one for storing the actual stack elements and another for keeping track of the minimum elements. This ensures that each operation can be performed in constant time. There is no feedback from previous generations, so I will proceed with this approach.


Generated:

class MinStack:
    def __init__(self):
        self.stack = []
        self.min_stack = []

    def push(self, x):
        self.stack.append(x)
        # If the min_stack is empty or the current element is smaller or equal to the top of the min_stack, push it onto the min_stack
        if not self.min_stack or x <= self.min_stack[-1]:
            self.min_stack.append(x)

    def pop(self):
        if self.stack:
            top = self.stack.pop()
            # If the popped element is the same as the top of the min_stack, pop it from the min_stack as well
            if top == self.min_stack[-1]:
                self.min_stack.pop()

    def getMin(self):
        # The top of the min_stack is the minimum element
        if self.min_stack:
            return self.min_stack[-1]
        return None

=== GENERATION END ===

=== EVALUATION START ===
Status: PASS
Feedback: 
The code correctly implements a stack with push, pop, and getMin operations, all in O(1) time complexity. The use of an auxiliary stack (min_stack) to keep track of the minimum values ensures that getMin can be performed in constant time. The code follows good style and best practices, with clear and concise comments explaining the logic. There are no improvements needed.

=== EVALUATION END ===
"""