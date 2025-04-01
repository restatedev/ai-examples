import hypercorn
import asyncio
import restate

from chat_session import chat_service
from loan_approval_workflow import loan_approval_wf
from utils.agent_session import agent_session
from utils.account import account
from utils.credit_worthiness_tools import credit_worthiness_svc

app = restate.app(
    services=[
        chat_service,
        loan_approval_wf,
        agent_session,
        account,
        credit_worthiness_svc,
    ]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9081"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
