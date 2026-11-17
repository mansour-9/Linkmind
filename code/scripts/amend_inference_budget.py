"""Explicit local operator amendment; never creates or resets a budget run."""
import argparse
from app.inference_budget import amend_limit

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected',required=True)
    parser.add_argument('--approved',required=True)
    parser.add_argument('--approval',required=True)
    parser.add_argument('--audit-path',required=True)
    args=parser.parse_args()
    receipt=amend_limit(args.expected,args.approved,args.approval,args.audit_path)
    print('Amended existing run',receipt['run_id'],'to USD',receipt['approved_limit'])

if __name__=='__main__':main()
