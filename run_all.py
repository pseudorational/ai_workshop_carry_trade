"""Run the full pipeline: gather -> signal -> execute (dry run) -> evaluate.

    python run_all.py            live FRED data
    python run_all.py --demo     offline synthetic data
    python run_all.py --send     also submit orders to the configured broker
"""
import sys

import step1_gather, step2_signal, step3_execute, step4_evaluate

if __name__ == "__main__":
    print("=" * 60, "\nSTEP 1  Gather data\n" + "=" * 60)
    step1_gather.main(demo="--demo" in sys.argv)
    print("\n" + "=" * 60, "\nSTEP 2  Pick the trade\n" + "=" * 60)
    step2_signal.main()
    print("\n" + "=" * 60, "\nSTEP 3  Send to trading system\n" + "=" * 60)
    step3_execute.main(send="--send" in sys.argv)
    print("\n" + "=" * 60, "\nSTEP 4  Evaluate\n" + "=" * 60)
    step4_evaluate.main()
