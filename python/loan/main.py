import hypercorn
import asyncio
import restate

from chat import chat_service
from loan_review_workflow import loan_review_workflow
from account import account
from utils.agent_session import agent_session
from utils.credit_worthiness_tools import credit_worthiness_svc

app = restate.app(
    services=[
        chat_service,
        loan_review_workflow,
        agent_session,
        account,
        credit_worthiness_svc,
    ]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9081"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
