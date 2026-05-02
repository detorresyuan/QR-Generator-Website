# WHAT IVE LEARNED FROM THIS PROJECT
# use while loops when in need of re-typing in userinput
# you cannot use typecasting of string and expect it to work
# you can convert it later from str to int using try_except using ValueError
# when using while loop, make sure to include all the nescessary functions inside

import math

print("CALCULATOR 9000!!!")

while True:
    A_input = input("Enter your first number: ")
    if A_input == "":
       print("Please enter a number.")
       continue
    try:
        A = float(A_input)
        break
    except ValueError:
       print("That is not a valid number, try again?")

print(f"The first number is set to: {A}")

pi = input("Do you want to use pi for your first number? (Y/N) ")
if pi == "Y":
    B = math.pi
else:
  while True:
    B_input = input("Enter your Second number: ")
    if B_input == "":
       print("Please enter a number.")
       continue
    try:
        B = float(B_input)
        break
    except ValueError:
       print("That is not a valid number, try again?")

print(f"The first number is set to: {B}")

Op = input("Enter your desired operator: (+, -, *, /)" )

if Op == "+":
    result = A + B
    print(round(result, 2))
elif Op == "-":
    result = A - B
    print(round(result, 2))
elif Op == "*":
    result = A * B
    print(round(result, 2))
elif Op == "/":
  while True:
    if B != 0:
        result = A / B
        print(round(result, 2))
        break
    else:
        B_new = float(input("You cannot divide by zero, enter another number: "))
        if B_new != 0:
               result = A / B_new
               print(round(result, 2))
               break
        #try:
           #B = float(B_new)
           #break
        #except ValueError:
           #print("This Bitch ass nigga!")
else:
    print("Goodbye.")