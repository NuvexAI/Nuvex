from agents.agent.tools.function.token_tool import comprehensive_token_analysis, comprehensive_pro_token_analysis
from agents.agent.tools.function.wallet_tool import sign_with_wallet, get_public_key

LOCAL_TOOL = [sign_with_wallet, get_public_key, comprehensive_token_analysis, comprehensive_pro_token_analysis]

def get_local_tool():
    return LOCAL_TOOL