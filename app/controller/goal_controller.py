from app.models.goal import Goal
from fastapi import HTTPException
from app.service.goal_service import create_goal, goals
from app.service.category_service import category_exists

def create_goal_controller(goal: Goal):
    try:
        if not goal.title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        if not goal.description.strip():
            raise HTTPException(status_code=400, detail="Description cannot be empty")
        
        if goal.expectedIncome <= 0:
            raise HTTPException(status_code=400, detail="Expected income must be a positive number")
        
        if goal.categoryId is not None and not isinstance(goal.categoryId, str):
            raise HTTPException(status_code=400, detail="Category ID must be a string")
        
        if goal.categoryId:
            if not category_exists(goal.categoryId):
                raise HTTPException(status_code=400, detail=f"Category with ID {goal.categoryId} does not exist")
        
        goal_id = create_goal(goal)
        return {"message": "Goal created successfully", "id": goal_id}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def goals_controller(monthYear):
    try:
        response = goals(monthYear)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))