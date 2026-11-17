"""Explicit local operator resume with preserved held reservations."""
import argparse
from app.inference_budget import resume_with_holds

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-reserved',required=True)
    parser.add_argument('--approval',required=True)
    parser.add_argument('--audit-path',required=True)
    args=parser.parse_args()
    result=resume_with_holds(args.expected_reserved,args.approval,args.audit_path)
    print('Resumed original run; held USD',result['reserved_usd'])

if __name__=='__main__':main()
