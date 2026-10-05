# Function 1: Get study hours
def get_hours():
    try:
        hours = int(input("Enter number of study hours: "))
        return hours
    except ValueError:
        print("Invalid input! Please enter numbers only.")
        return None


# Function 2: Calculate break time
def calculate_break(hours):
    break_time = hours * 10
    return break_time


# Function 3: Check focus level
def focus_level(hours):
    if hours >= 5:
        return "High Focus"
    elif hours >= 3:
        return "Moderate Focus"
    else:
        return "Low Focus"


# Function 4: Study advice
def give_advice(level):
    if level == "High Focus":
        return "Great job! Maintain this routine."
    elif level == "Moderate Focus":
        return "Try to increase study time slightly."
    else:
        return "You should improve your study routine."


# Function 5: Display result
def display_result(hours, break_time, level, advice):
    print("Study Hours:", hours)
    print("Recommended Break Time:", break_time, "minutes")
    print("Focus Level:", level)
    print("Advice:", advice)


# Main Program
print("Smart Study Break Reminder System")

hours = get_hours()

if hours is not None:
    break_time = calculate_break(hours)
    level = focus_level(hours)
    advice = give_advice(level)
    display_result(hours, break_time, level, advice)
else:
    print("Program stopped due to invalid input.")