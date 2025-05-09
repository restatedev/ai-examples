## Long-lived multi-agent setups

**Note:** We didn't need to change anything in the agent loop to make this work. 

If you **combine Restate Virtual Objects with Restate's scheduling capabilities**, then you can build long-lived, autonomous, proactive agents which periodically come to live, for example, because of a trigger or a timer. Then, they do some tasks and possibly schedule follow-up tasks for later. 

Different agent sessions could communicate with each other and distribute work among them. Each agent being its own Virtual Object.

For example, you could have a crew of specialized agents continuously monitoring social media or marketing campaigns and taking action based on what happens.

**Restate would make this setup resilient, consistent, scalable, observable, and would let you run it on serverless infrastructure.**
