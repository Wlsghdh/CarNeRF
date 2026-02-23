from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Vehicle, DiagnosisReport
from app.schemas import VehicleOut, DiagnosisOut

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


@router.get("/", response_model=list[VehicleOut])
def list_vehicles(
    brand: Optional[str] = None,
    fuel_type: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Vehicle)
    if brand:
        q = q.filter(Vehicle.brand == brand)
    if fuel_type:
        q = q.filter(Vehicle.fuel_type == fuel_type)
    if year_min:
        q = q.filter(Vehicle.year >= year_min)
    if year_max:
        q = q.filter(Vehicle.year <= year_max)
    return q.all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")
    return vehicle


@router.get("/{vehicle_id}/diagnosis", response_model=DiagnosisOut)
def get_diagnosis(vehicle_id: int, db: Session = Depends(get_db)):
    report = db.query(DiagnosisReport).filter(DiagnosisReport.vehicle_id == vehicle_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="진단 리포트가 없습니다.")
    return report
