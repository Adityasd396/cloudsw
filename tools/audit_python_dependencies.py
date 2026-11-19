"""Read-only OSV audit of installed production dependency closure, no user data."""
import importlib.metadata as metadata
import json
from pathlib import Path
from packaging.requirements import Requirement
import requests

ROOT=Path(__file__).resolve().parents[1]
def run(output):
    queue=['Flask','waitress','Pillow','tzdata'];resolved={}
    while queue:
        name=queue.pop();distribution=metadata.distribution(name);key=distribution.metadata['Name']
        if key.lower() in {n.lower() for n in resolved}:continue
        resolved[key]=distribution.version
        for requirement in distribution.requires or []:
            parsed=Requirement(requirement)
            if not parsed.marker or parsed.marker.evaluate({'extra':''}):queue.append(parsed.name)
    result={'packages':resolved,'service':'https://api.osv.dev/v1/querybatch','scope':'installed production dependency closure only'}
    response=requests.post(result['service'],json={'queries':[{'package':{'ecosystem':'PyPI','name':name},'version':version} for name,version in resolved.items()]},timeout=30)
    response.raise_for_status();result['results']={name:item.get('vulns',[]) for name,item in zip(resolved,response.json()['results'])}
    Path(output).write_text(json.dumps(result,indent=2));print(json.dumps(result));return result
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'.openai/dependency-python-launch.json'));args=parser.parse_args();run(args.output)
