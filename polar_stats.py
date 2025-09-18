
import math

def compute_polar_stats(points, cx, cy, target_R, bins=720, robust="median",
                        kernel_smooth=True, kernel_halfwidth_bins=2):
    """
    points: list of {"x": float, "y": float}
    Returns dict with keys: R_ref, sigma, sigma_rel, mae, max_abs, rho_theta (list), theta_bins (list)
    """
    if len(points) < 20:
        raise ValueError("Too few points to analyze.")

    polar = []
    for p in points:
        x, y = float(p["x"]), float(p["y"])
        dx, dy = x - cx, y - cy
        r = (dx*dx + dy*dy) ** 0.5
        th = math.atan2(dy, dx)
        if th < 0:
            th += 2*math.pi
        polar.append((th, r))

    bin_lists = [[] for _ in range(bins)]
    for th, r in polar:
        k = int(th / (2*math.pi) * bins)
        if k == bins:
            k = bins - 1
        bin_lists[k].append(r)

    rho, theta_bins = [], []
    for k in range(bins):
        th = (k + 0.5) * (2*math.pi / bins)
        theta_bins.append(th)
        arr = bin_lists[k]
        if not arr:
            rho.append(float('nan'))
        else:
            if robust == "median":
                s = sorted(arr)
                m = s[len(s)//2] if len(s)%2==1 else 0.5*(s[len(s)//2-1]+s[len(s)//2])
                rho.append(m)
            else:
                rho.append(sum(arr)/len(arr))

    import math as _m
    for i in range(bins):
        if _m.isnan(rho[i]):
            left = right = None
            for d in range(1, bins):
                li = (i - d) % bins
                ri = (i + d) % bins
                if left is None and not _m.isnan(rho[li]):
                    left = rho[li]
                if right is None and not _m.isnan(rho[ri]):
                    right = rho[ri]
                if left is not None or right is not None:
                    break
            if left is not None and right is not None:
                rho[i] = 0.5*(left+right)
            elif left is not None:
                rho[i] = left
            elif right is not None:
                rho[i] = right
            else:
                rho[i] = 0.0

    if kernel_smooth and kernel_halfwidth_bins > 0:
        smoothed = [0.0]*bins
        W = 2*kernel_halfwidth_bins + 1
        for i in range(bins):
            acc = 0.0
            for d in range(-kernel_halfwidth_bins, kernel_halfwidth_bins+1):
                acc += rho[(i+d) % bins]
            smoothed[i] = acc / W
        rho = smoothed

    R_ref = float(target_R)
    sqe = [(ri - R_ref)**2 for ri in rho]
    sigma = (sum(sqe) / bins) ** 0.5
    mae = sum(abs(ri - R_ref) for ri in rho) / bins
    max_abs = max(abs(ri - R_ref) for ri in rho)
    sigma_rel = (sigma / R_ref) if R_ref > 1e-9 else float('inf')

    return {
        "R_ref": R_ref,
        "sigma": float(sigma),
        "sigma_rel": float(sigma_rel),
        "mae": float(mae),
        "max_abs": float(max_abs),
        "rho_theta": rho,
        "theta_bins": theta_bins
    }
