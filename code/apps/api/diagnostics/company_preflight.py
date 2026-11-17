"""Read-only Sonnet/Titan access and current pricing; never invokes a model."""
import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

import boto3
from botocore.config import Config

SONNET = "us.anthropic.claude-sonnet-4-6"
EMBEDDING = "amazon.titan-embed-text-v2:0"
REGION = "us-east-1"


def pricing():
    result = {}
    for offer, model in (("AmazonBedrockFoundationModels", SONNET), ("AmazonBedrock", EMBEDDING)):
        url=f"https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/{offer}/current/{REGION}/index.json"
        with urlopen(url,timeout=45) as response:
            catalog=json.load(response)
        rate=dict(currency="USD",source=url,published=catalog["publicationDate"],dimensions=[])
        for sku, product in catalog["products"].items():
            attributes=product["attributes"]
            if model==SONNET:
                applies=attributes.get("model")=="Claude Sonnet 4.6" and attributes.get("feature")=="On-demand Inference" and attributes.get("usagetype") in {"USE1-MP:USE1_InputTokenCount-Units","USE1-MP:USE1_OutputTokenCount-Units"}
            else:
                label=" ".join(str(attributes.get(k,"")) for k in ("model","modelName","usagetype")).lower()
                applies=attributes.get("feature")=="On-demand Inference" and "titan" in label and ("embed" in label) and ("v2" in label or "v 2" in label or "v-2" in label)
            if not applies:
                continue
            for term in catalog["terms"]["OnDemand"].get(sku,{}).values():
                for dimension in term["priceDimensions"].values():
                    scale={"1M tokens":1,"1K tokens":1000,"tokens":1_000_000}.get(dimension["unit"])
                    if scale is None:
                        continue
                    direction=attributes.get("inferenceType","").lower()
                    if "input" in direction or model==EMBEDDING:
                        key="input"
                    elif "output" in direction:
                        key="output"
                    else:
                        continue
                    value=Decimal(dimension["pricePerUnit"]["USD"])*scale
                    if key in rate and Decimal(rate[key])!=value:
                        raise ValueError("Ambiguous applicable model price")
                    rate[key]=str(value)
                    rate["effective_date"]=term["effectiveDate"][:10]
                    rate["dimensions"].append(dict(sku=sku,unit=dimension["unit"],usage=attributes.get("usagetype"),effective=term["effectiveDate"]))
        if model==EMBEDDING:
            rate["output"]="0"
        if not all(key in rate for key in ("input","output","effective_date")):
            raise ValueError("Current model token prices could not be verified")
        rate["input"]=float(rate["input"])
        rate["output"]=float(rate["output"])
        result[model]=rate
    return {REGION:result}


def preflight():
    session=boto3.Session(region_name=REGION)
    config=Config(retries={"mode":"standard","total_max_attempts":1},connect_timeout=5,read_timeout=30)
    session.client("sts",config=config).get_caller_identity()
    control=session.client("bedrock",config=config)
    profile=control.get_inference_profile(inferenceProfileIdentifier=SONNET)
    embedding=control.get_foundation_model(modelIdentifier=EMBEDDING)
    if profile["status"]!="ACTIVE":
        raise ValueError("Sonnet profile is not active")
    return dict(authenticated=True,region=REGION,sonnet_profile=SONNET,sonnet_active=True,
        embedding_model=embedding["modelDetails"]["modelId"],inference_calls=0)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--pricing-only",action="store_true")
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    try:
        rates=pricing()
        (args.out/"rates.json").write_text(json.dumps(rates,indent=2)+"\n",encoding="utf-8")
        report=dict(pricing_verified=True,access=preflight() if not args.pricing_only else "not_checked")
        (args.out/"preflight.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report))
        return 0
    except Exception as exc:
        # Preserve useful error classes without account identifiers or credential material.
        print(json.dumps(dict(status="preflight_failed",error=type(exc).__name__,inference_calls=0)))
        return 2


if __name__=="__main__":
    sys.exit(main())
