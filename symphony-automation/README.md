# Symphony Automation

## Use

One each machine to be configured:

1. Install ansible
2. Run the role-appropriate command below

### Master management node:
```bash
ansible-playbook --tags=master --extra-vars='{"cos": {"install_bucket": "hpc-install-symphony", "access_key_id": "abc", "secret_access_key": "xyz"}, "failover": {"ip": "1.2.3.4", "hostname": "symphony-master-1", "domain": "hpc.local"}, "nfs_mount": "xyz"}' playbooks/all.yaml
```

### Failover management node:
```bash
ansible-playbook --tags=failover --extra-vars='{"cos": {"install_bucket": "hpc-install-symphony", "access_key_id": "abc", "secret_access_key": "xyz"}, "master": {"ip": "1.2.3.4", "hostname": "symphony-master-0", "domain": "hpc.local"}, "nfs_mount": "xyz"}' playbooks/all.yaml
```

### Compute node:
```bash
ansible-playbook --tags=compute --extra-vars='{"cos": {"install_bucket": "hpc-install-symphony", "access_key_id": "abc", "secret_access_key": "xyz"}, "master": {"ip": "1.2.3.4", "hostname": "symphony-master-0", "domain": "hpc.local"}, "failover": {"ip": "1.2.3.4", "hostname": "symphony-master-1", "domain": "hpc.local"}}' playbooks/all.yaml
```

## Description of extra-vars

- cos.install_bucket - the COS bucket where the symphony install binaries and entitlement file can be sourced (for now, these are all sourced from the same bucket, but they may ultimately come from different sources.  E.g., customer places entitlement file in a prescribed location within the image).
- cos.access_key_id, cos.secret_access_key - the COS credentials with read access to the install bucket.
- master/failover - the ip address, hostname, and domain name of the master or failover machines. Both managers (master and failover) have to be aware of one another, and each compute node needs to be aware of both managers.
- nfs_mount - the mountpoint for the shared filesystem (IBM Cloud File Storage), to be used as a shared configuration repository between management nodes.
