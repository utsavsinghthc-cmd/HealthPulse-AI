from fastapi import APIRouter

from app.analytics.cluster_engine import build_cluster_report


router = APIRouter(
    prefix="/api",
    tags=["Clusters"],
)


@router.get("/clusters")
def get_clusters():
    report = build_cluster_report()

    clusters = report["clusters"]

    high_risk = clusters[
        clusters["cluster_level"] == "HIGH"
    ]

    return {
        "status": "success",
        "latest_date": str(report["latest_date"]),
        "total_clusters": int(len(clusters)),
        "high_risk_clusters": int(len(high_risk)),
        "clusters": clusters.to_dict(
            orient="records"
        ),
        "high_risk": high_risk.to_dict(
            orient="records"
        ),
    }