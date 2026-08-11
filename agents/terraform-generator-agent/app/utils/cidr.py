from ipaddress import IPv4Network, ip_network


def allocate_subnet(vpc_cidr: str, used_cidrs: list[str], preferred: str | None = None, prefixlen: int = 24) -> str | None:
    try:
        vpc = ip_network(vpc_cidr, strict=False)
    except ValueError:
        return None
    used = []
    for value in used_cidrs:
        try:
            used.append(ip_network(value, strict=False))
        except ValueError:
            continue
    candidates: list[IPv4Network] = []
    if preferred:
        try:
            candidates.append(ip_network(preferred, strict=False))
        except ValueError:
            pass
    if vpc.prefixlen <= prefixlen:
        candidates.extend(vpc.subnets(new_prefix=prefixlen))
    for candidate in candidates:
        if not candidate.subnet_of(vpc):
            continue
        if any(candidate.overlaps(existing) for existing in used):
            continue
        return str(candidate)
    return None
