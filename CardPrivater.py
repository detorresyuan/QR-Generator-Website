while True:
    print("Please insert credit card num at this format XXXX-XXXX-XXXX-XXXX")
    assignmentNum = input("Please enter card number: \n")
    index = len(assignmentNum)

    if index == 19:
        lastDigits = assignmentNum[-4:]
        if lastDigits[-4:]:
            print(f"XXXX-XXXX-XXXX-{lastDigits[-4:]}")
            break
    else:
     print("Please insert all the digits of your credit card.")