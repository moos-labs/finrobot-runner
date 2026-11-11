#!/usr/bin/env python3
"""FinRobot real run for the Borsagator fleet.

Market Analyst agent with YFinance toolkits only (no key-gated data
sources), driven by Cohere's OpenAI-compatible endpoint using the
COHERE_API_KEY org secret -- the same route that powers TradingAgents.

Writes results/analysis.md and results/finrobot_result.json.
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="AAPL")
    args = ap.parse_args()
    ticker = args.ticker.upper()
    results = Path("results")
    results.mkdir(exist_ok=True)
    key = os.environ.get("COHERE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        (results / "finrobot_result.json").write_text(json.dumps(
            {"tool": "finrobot", "ticker": ticker, "status": "error",
             "error": "no COHERE_API_KEY in env"}))
        return 1
    model = os.environ.get("FINROBOT_MODEL", "command-r-08-2024")
    llm_config = {
        "config_list": [{
            "model": model,
            "api_key": key,
            "base_url": "https://api.cohere.ai/compatibility/v1",
        }],
        "temperature": 0.2,
        "timeout": 300,
    }
    from typing import Annotated

    from finrobot.data_source.yfinance_utils import YFinanceUtils
    from finrobot.agents.workflow import SingleAssistant

    # Cohere's tool-schema validator rejects any parameter whose JSON
    # schema lacks a "type" (the TradingAgents lesson). YFinanceUtils'
    # own signatures use a custom SavePathType / Optional[str] for
    # save_path, which AG2 renders typeless -- so the agent gets these
    # plainly-typed wrappers instead (no save_path parameters at all).
    def get_stock_data(
        symbol: Annotated[str, "ticker symbol"],
        start_date: Annotated[str, "start date, YYYY-mm-dd"],
        end_date: Annotated[str, "end date, YYYY-mm-dd"],
    ) -> str:
        """retrieve stock price data for designated ticker symbol"""
        df = YFinanceUtils.get_stock_data(symbol, start_date, end_date)
        return df.tail(120).to_string()

    def get_stock_info(
        symbol: Annotated[str, "ticker symbol"],
    ) -> str:
        """fetches and returns latest stock information"""
        return json.dumps(YFinanceUtils.get_stock_info(symbol), default=str)

    def get_company_info(
        symbol: Annotated[str, "ticker symbol"],
    ) -> str:
        """fetches and returns company information"""
        df = YFinanceUtils.get_company_info(symbol)
        return df.to_string()

    def get_analyst_recommendations(
        symbol: Annotated[str, "ticker symbol"],
    ) -> str:
        """fetches the latest analyst recommendations"""
        return str(YFinanceUtils.get_analyst_recommendations(symbol))

    profile = (
        "As a Market Analyst, one must possess strong analytical and "
        "problem-solving abilities, collect necessary financial information "
        "and aggregate them based on client's requirement. For coding tasks, "
        "only use the functions you have been provided with. Reply TERMINATE "
        "when the task is done."
    )
    config = {
        "name": "Market_Analyst",
        "profile": profile,
        "toolkits": [
            get_stock_data,
            get_stock_info,
            get_company_info,
            get_analyst_recommendations,
        ],
    }
    agent = SingleAssistant(config, llm_config=llm_config)
    prompt = (
        f"Analyze the stock {ticker}. First use your tools to fetch its "
        f"recent daily price data, company info and analyst recommendations. "
        f"Then write a concise analysis: trend, momentum, key levels, risks, "
        f"and end with a line exactly like "
        f"'VERDICT: bullish - one sentence reason' (or bearish / neutral). "
        f"Reply TERMINATE at the very end."
    )
    agent.chat(prompt)

    msgs = []
    try:
        hist = agent.user_proxy.chat_messages.get(agent.assistant, [])
        for m in hist:
            c = (m.get("content") or "").strip()
            if c:
                msgs.append({"name": m.get("name"), "role": m.get("role"),
                             "content": c})
    except Exception:
        pass
    analysis = ""
    for m in reversed(msgs):
        if m.get("name") == "Market_Analyst" and len(m["content"]) > 200:
            analysis = m["content"]
            break
    transcript = "\n\n".join(
        f"### {m.get('name') or m.get('role')}\n{m['content']}" for m in msgs)
    (results / "analysis.md").write_text(
        f"# FinRobot - {ticker}\n\nModel: {model} (Cohere via its "
        f"OpenAI-compatible endpoint)\n\n## Analysis\n\n"
        f"{analysis or '(no long-form analysis captured)'}\n\n"
        f"## Full transcript\n\n{transcript}\n")
    verdict = ""
    for line in (analysis or "").splitlines():
        if "VERDICT:" in line.upper():
            verdict = line.strip()
    out = {"tool": "finrobot", "ticker": ticker, "model": model,
           "messages": len(msgs), "analysis_chars": len(analysis),
           "verdict": verdict}
    (results / "finrobot_result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out))
    return 0 if analysis else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        Path("results").mkdir(exist_ok=True)
        (Path("results") / "finrobot_result.json").write_text(json.dumps(
            {"tool": "finrobot", "status": "error",
             "error": traceback.format_exc()[-500:]}))
        sys.exit(1)
