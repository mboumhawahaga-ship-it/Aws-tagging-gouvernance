def cleanup_ec2_instances():
    print("🖥️  Scan EC2...")
    res = {"scanned": 0, "already_terminated": 0, "non_compliant": 0, "deleted": 0, "in_grace_period": 0}
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reser in page['Reservations']:
                for inst in reser['Instances']:
                    instance_id = inst['InstanceId'] # <-- Correction de 'id'
                    state = inst.get('State', {}).get('Name')
                    res["scanned"] += 1

                    if state in ['terminated', 'terminating']:
                        res["already_terminated"] += 1
                        continue

                    compliant, _ = check_required_tags(inst.get('Tags', []))
                    if not compliant:
                        res["non_compliant"] += 1 # Toujours compter la non-conformité
                        if is_within_grace_period(inst.get('LaunchTime')):
                            res["in_grace_period"] += 1
                            continue
                        
                        if not DRY_RUN:
                            ec2_client.terminate_instances(InstanceIds=[instance_id])
                            res["deleted"] += 1
    except Exception as e: res["errors"] = str(e)
    return res

def cleanup_lambda_functions():
    print("⚡ Scan Lambda...")
    res = {"scanned": 0, "non_compliant": 0, "deleted": 0}
    try:
        for f in lambda_client.list_functions()['Functions']:
            name = f['FunctionName']
            if name == os.environ.get('AWS_LAMBDA_FUNCTION_NAME'): continue
            res["scanned"] += 1
            
            tags = lambda_client.list_tags(Resource=f['FunctionArn']).get('Tags', {})
            compliant, _ = check_required_tags([{'Key': k, 'Value': v} for k, v in tags.items()])
            
            if not compliant:
                res["non_compliant"] += 1 # <-- Correction de Claude ajoutée ici
                if not DRY_RUN:
                    lambda_client.delete_function(FunctionName=name)
                    res["deleted"] += 1
    except Exception as e: res["errors"] = str(e)
    return res
