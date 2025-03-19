from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from motor.motor_asyncio import AsyncIOMotorClient

# Import your database instance
from config.database import db

# Define collections (adjust names as needed)
sales_collection = db.downtown_sales
invoices_collection = db.downtown_invoices
expenses_collection = db.downtown_expenses
purchases_collection = db.downtown_purchases
staff_collection = db.downtown_staffs
customers_collection = db.downtown_customers  # New collection for customers



router = APIRouter()


# Pydantic response model for stats
class StatsResponse(BaseModel):
    total_direct_sales: Dict[str, Any] = Field(
        ..., description="Direct sales count and total amount"
    )
    total_process_sales: Dict[str, Any] = Field(
        ..., description="Process sales (invoices with status 'completed') count and total amount"
    )
    total_kg: float = Field(..., description="Total kg from completed invoices")
    total_expenses: Dict[str, Any] = Field(
        ..., description="Expenses count and total amount"
    )
    total_purchase_kg: float = Field(..., description="Total purchase kg")
    total_purchase_amount: float = Field(..., description="Total purchase amount")
    total_customers: int = Field(..., description="Total number of customers")
    total_staff_count: int = Field(..., description="Total staff count")

class MonthlyKgResponse(BaseModel):
    labels: List[str]
    kgCounts: List[float]# Response model for monthly sales data
    
    
class MonthlySalesResponse(BaseModel):
    labels: List[str]
    salesAmounts: List[float]

# Response model for process type count data
class ProcessTypeCountResponse(BaseModel):
    labels: List[str]
    counts: List[int]
    
class RecyclerMonthlyComparisonResponse(BaseModel):
    labels: List[str]
    recyclerA: List[float]
    recyclerB: List[float]

class MonthlyProcessSalesResponse(BaseModel):
    labels: List[str]
    salesAmounts: List[float]
        
class TopCustomersResponse(BaseModel):
    labels: List[str]
    salesAmounts: List[float]



@router.get("/all", response_model=StatsResponse)
async def get_stats():
    # ------------------------
    # Total Direct Sales from the sales collection
    # ------------------------
    sales_agg = await sales_collection.aggregate([
        {
            "$group": {
                "_id": None,
                "totalAmount": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        }
    ]).to_list(length=1)

    if sales_agg:
        direct_sales_count = sales_agg[0]["count"]
        direct_sales_amount = sales_agg[0]["totalAmount"]
    else:
        direct_sales_count = 0
        direct_sales_amount = 0.0

    # ------------------------
    # Total Process Sales from invoices with status "completed"
    # ------------------------
    process_invoices_agg = await invoices_collection.aggregate([
    {
        "$group": {
            "_id": None,
            "totalAmount": {"$sum": "$amount"},
            "count": {"$sum": 1},
            "totalKg": {"$sum": "$kgIn"}  # change to "kgOut" if needed
        }
    }
        ]).to_list(length=1)


    if process_invoices_agg:
        process_sales_count = process_invoices_agg[0]["count"]
        process_sales_amount = process_invoices_agg[0]["totalAmount"]
        total_kg = process_invoices_agg[0]["totalKg"]
    else:
        process_sales_count = 0
        process_sales_amount = 0.0
        total_kg = 0.0

    # ------------------------
    # Total Expenses from the expenses collection
    # ------------------------
    expenses_agg = await expenses_collection.aggregate([
        {
            "$group": {
                "_id": None,
                "totalAmount": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        }
    ]).to_list(length=1)
    if expenses_agg:
        expenses_count = expenses_agg[0]["count"]
        expenses_amount = expenses_agg[0]["totalAmount"]
    else:
        expenses_count = 0
        expenses_amount = 0.0

    # ------------------------
    # Total Purchases from the purchases collection
    # ------------------------
    purchases_agg = await purchases_collection.aggregate([
        {
            "$group": {
                "_id": None,
                "totalKg": {"$sum": "$kg"},
                "totalAmount": {"$sum": "$amount"}
            }
        }
    ]).to_list(length=1)
    if purchases_agg:
        purchase_kg = purchases_agg[0]["totalKg"]
        purchase_amount = purchases_agg[0]["totalAmount"]
    else:
        purchase_kg = 0.0
        purchase_amount = 0.0

    # ------------------------
    # Total Customers from the customers collection
    # ------------------------
    total_customers = await customers_collection.count_documents({})

    # ------------------------
    # Total Staff Count from the staff collection
    # ------------------------
    staff_count = await staff_collection.count_documents({})

    # ------------------------
    # Return aggregated stats
    # ------------------------
    return StatsResponse(
        total_direct_sales={"count": direct_sales_count, "amount": direct_sales_amount},
        total_process_sales={"count": process_sales_count, "amount": process_sales_amount},
        total_kg=total_kg,
        total_expenses={"count": expenses_count, "amount": expenses_amount},
        total_purchase_kg=purchase_kg,
        total_purchase_amount=purchase_amount,
        total_customers=total_customers,
        total_staff_count=staff_count
    )


@router.get("/monthly-kg", response_model=MonthlyKgResponse)
async def get_monthly_invoice_kg():
    """
    Aggregates invoice kg data by month for the current year.
    Assumes invoice documents have:
      - `date`: a string in "YYYY-MM-DD" format
      - `kgIn`: a numeric value
    """
    invoices_collection = db.downtown_invoices  # Adjust collection name as needed

   
    current_year = datetime.now().strftime("%Y")

    pipeline = [
        {
            "$match": {
                "date": {"$regex": f"^{current_year}"}  # Only invoices for current year
            }
        },
        {
            "$group": {
                "_id": {"$substr": ["$date", 5, 2]},  # Extract month (e.g., "01" for January)
                "totalKg": {"$sum": "$kgIn"}
            }
        },
        {"$sort": {"_id": 1}}  # Sort by month
    ]
    try:
        monthly_data = await invoices_collection.aggregate(pipeline).to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Map month numbers to abbreviated names.
    month_map = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec",
    }

    # Create a dictionary for the aggregated data
    monthly_dict = {data["_id"]: data["totalKg"] for data in monthly_data}

    # Build arrays of labels and kgCounts for all 12 months (default to 0 if no data)
    labels = []
    kg_counts = []
    for month in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
        labels.append(month_map[month])
        kg_counts.append(monthly_dict.get(month, 0))

    return MonthlyKgResponse(labels=labels, kgCounts=kg_counts)


@router.get("/sales/monthly-sales", response_model=MonthlySalesResponse)
async def get_monthly_sales():
    """
    Aggregates monthly sales data for the current year.
    Assumes each sale document has:
      - date: a string in "YYYY-MM-DD" format
      - amount: a numeric field representing the sale value in NGN
    """
    sales_collection = db.downtown_sales  # Adjust collection name as needed

    # Get current year as a string, e.g., "2025"
    current_year = datetime.now().strftime("%Y")

    pipeline = [
        {
            "$match": {
                "date": {"$regex": f"^{current_year}"}  # Filter for current year
            }
        },
        {
            "$group": {
                "_id": {"$substr": ["$date", 5, 2]},  # Extract month from "YYYY-MM-DD"
                "totalSales": {"$sum": "$amount"}
            }
        },
        {"$sort": {"_id": 1}}  # Ensure results are sorted by month
    ]

    try:
        monthly_data = await sales_collection.aggregate(pipeline).to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Map month numbers to abbreviated names.
    month_map = {
        "01": "Jan",
        "02": "Feb",
        "03": "Mar",
        "04": "Apr",
        "05": "May",
        "06": "Jun",
        "07": "Jul",
        "08": "Aug",
        "09": "Sep",
        "10": "Oct",
        "11": "Nov",
        "12": "Dec"
    }

    # Build a dictionary from the aggregation result for quick lookup
    monthly_dict = {data["_id"]: data["totalSales"] for data in monthly_data}

    # Create arrays for labels and salesAmounts for all 12 months (defaulting to 0 if no data exists)
    labels = []
    salesAmounts = []
    for month in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
        labels.append(month_map[month])
        salesAmounts.append(monthly_dict.get(month, 0))

    return MonthlySalesResponse(labels=labels, salesAmounts=salesAmounts)


@router.get("/process/process-type-count", response_model=ProcessTypeCountResponse)
async def get_process_type_count():
    """
    Aggregates the count of invoices by process type for invoices with status "completed."
    Assumes each invoice document has:
      - status: a string (only "completed" invoices are considered)
      - processType: a list of process type codes (e.g., ["R"], ["C"], ["B"], ["R", "C"], etc.)
    """
    invoices_collection = db.downtown_invoices  # Adjust collection name as needed

    pipeline = [
        {
            "$match": {
                "status": "completed"
            }
        },
        # Use $setUnion to get distinct values from processType array.
        {
            "$set": {
                "sortedProcessType": { "$setUnion": ["$processType", []] }
            }
        },
        # Reduce the array into a single string separated by hyphens.
        {
            "$set": {
                "processTypeKey": {
                    "$reduce": {
                        "input": "$sortedProcessType",
                        "initialValue": "",
                        "in": {
                            "$cond": [
                                { "$eq": ["$$value", ""] },
                                "$$this",
                                { "$concat": ["$$value", "-", "$$this"] }
                            ]
                        }
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$processTypeKey",
                "count": { "$sum": 1 }
            }
        },
        { "$sort": { "_id": 1 } }
    ]

    try:
        agg_result = await invoices_collection.aggregate(pipeline).to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build a dictionary from the aggregation results.
    result_dict = {doc["_id"]: doc["count"] for doc in agg_result if doc["_id"] is not None}

    # Define a mapping from the keys produced by our pipeline (alphabetically sorted) to our expected keys.
    # For example, if an invoice has processType ["R", "C"], $setUnion will yield ["C", "R"], 
    # which reduces to "C-R". We want to remap that to "R-C".
    expected_mapping = {
        "R": "R",
        "C": "C",
        "B": "B",
        "B-C": "C-B",   # if only Crushing and Blending, sorted yields ["B", "C"] → "B-C", remap to "C-B"
        "B-R": "R-B",   # if Recycling and Blending, sorted yields ["B", "R"] → "B-R", remap to "R-B"
        "C-R": "R-C",   # if Recycling and Crushing, sorted yields ["C", "R"] → "C-R", remap to "R-C"
        "B-C-R": "R-C-B"  # if all three, sorted yields ["B", "C", "R"] → "B-C-R", remap to "R-C-B"
    }

    # Normalize the keys according to the expected mapping.
    normalized_result = {}
    for key, count in result_dict.items():
        new_key = expected_mapping.get(key, key)
        # If the key already exists, add the count.
        normalized_result[new_key] = normalized_result.get(new_key, 0) + count

    # Define the fixed labels in the desired order.
    fixed_labels = ["R", "C", "B", "R-C", "R-B", "C-B", "R-C-B"]
    counts = [normalized_result.get(label, 0) for label in fixed_labels]

    return ProcessTypeCountResponse(labels=fixed_labels, counts=counts)




@router.get("/rec/recycler-monthly-comparison", response_model=RecyclerMonthlyComparisonResponse)
async def get_recycler_monthly_comparison():
    """
    Aggregates monthly kg data (using the `kgIn` field) for invoices with status "completed"
    and with a recycler value ("a" or "b"). The invoices are grouped by the month extracted
    from the `date` field and then by the recycler field. The results are "pivoted" so that for
    each month (from Jan to Dec) you have separate totals for Recycler A and Recycler B.
    """
    invoices_collection = db.downtown_invoices  # Adjust as needed

    pipeline = [
        {
            "$match": {
                 "recycler": {"$in": ["a", "b"]}
            }
        },
        # Group by month (extracted from the date) and recycler
        {
            "$group": {
                "_id": {
                    "month": { "$substr": ["$date", 5, 2] },
                    "recycler": "$recycler"
                },
                "totalKg": { "$sum": "$kgIn" }
            }
        },
        # Now group by month only, and accumulate an array with recycler data
        {
            "$group": {
                "_id": "$_id.month",
                "data": {
                    "$push": {
                        "recycler": "$_id.recycler",
                        "totalKg": "$totalKg"
                    }
                }
            }
        },
        { "$sort": { "_id": 1 } }
    ]

    try:
        agg_result = await invoices_collection.aggregate(pipeline).to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Map month numbers to abbreviated names.
    month_map = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }

    # Create a dictionary mapping month (as two-digit string) to its aggregated recycler data.
    month_data = {doc["_id"]: doc["data"] for doc in agg_result}

    labels = []
    recyclerA = []
    recyclerB = []
    # Iterate over all 12 months so that months with no data default to 0.
    for m in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
        labels.append(month_map[m])
        a_total = 0.0
        b_total = 0.0
        if m in month_data:
            for entry in month_data[m]:
                if entry["recycler"].lower() == "a":
                    a_total += entry["totalKg"]
                elif entry["recycler"].lower() == "b":
                    b_total += entry["totalKg"]
        recyclerA.append(a_total)
        recyclerB.append(b_total)

    return RecyclerMonthlyComparisonResponse(
        labels=labels,
        recyclerA=recyclerA,
        recyclerB=recyclerB
    )
    
    
    

@router.get("/mon/monthly-process-sales", response_model=MonthlyProcessSalesResponse)
async def get_monthly_process_sales():
    """
    Aggregates monthly sales data (using the invoice `amount` field) for invoices with status "completed"
    for the current year.
    Assumes each invoice document has:
      - date: a string in "YYYY-MM-DD" format
      - amount: a numeric field representing the sale value in NGN
      - status: a string that should be "completed" for processed invoices
    """
    invoices_collection = db.downtown_invoices  # Adjust collection name as needed

    # Filter invoices for the current year (e.g., "2025")
    current_year = datetime.now().strftime("%Y")

    pipeline = [
        {
            "$match": {
                "status": "completed",
                "date": {"$regex": f"^{current_year}"}
            }
        },
        {
            "$group": {
                "_id": { "$substr": ["$date", 5, 2] },  # Extract month portion
                "totalSales": { "$sum": "$amount" }
            }
        },
        { "$sort": { "_id": 1 } }
    ]

    try:
        agg_result = await invoices_collection.aggregate(pipeline).to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Map month numbers to abbreviated names.
    month_map = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"
    }

    # Build a dictionary of month -> total sales.
    monthly_dict = {doc["_id"]: doc["totalSales"] for doc in agg_result}

    labels = []
    salesAmounts = []
    # Ensure all 12 months are represented (defaulting to 0 if missing).
    for month in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
        labels.append(month_map[month])
        salesAmounts.append(monthly_dict.get(month, 0))

    return MonthlyProcessSalesResponse(labels=labels, salesAmounts=salesAmounts) 
    
    

@router.get("/cus/top-customers", response_model=TopCustomersResponse)
async def get_top_customers():
    """
    Aggregates the top 5 customers by total invoice amount from invoices with status "completed".
    Assumes each invoice document has:
      - status: a string ("completed" for processed invoices)
      - amount: a numeric field representing the sale value
      - customer: an embedded document with a "name" field
    """
    invoices_collection = db.downtown_invoices  # Adjust collection name as needed

    pipeline = [
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$customer.name",  # Group by customer name
            "totalSales": {"$sum": "$amount"}
        }},
        {"$sort": {"totalSales": -1}},  # Sort descending by total sales
        {"$limit": 5}
    ]

    try:
        agg_result = await invoices_collection.aggregate(pipeline).to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    labels = [doc["_id"] for doc in agg_result]
    salesAmounts = [doc["totalSales"] for doc in agg_result]

    return TopCustomersResponse(labels=labels, salesAmounts=salesAmounts)