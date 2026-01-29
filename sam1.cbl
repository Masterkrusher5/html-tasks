       IDENTIFICATION DIVISION.
       PROGRAM-ID. BANKACCT.

      *============================================*
      *  SIMPLE BANK ACCOUNT MANAGEMENT PROGRAM   *
      *============================================*

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCT-FILE ASSIGN TO "ACCOUNT.DAT"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  ACCT-FILE.
       01  ACCT-RECORD.
           05 ACCT-NUMBER       PIC 9(10).
           05 ACCT-NAME         PIC X(30).
           05 ACCT-BALANCE      PIC 9(9)V99.

       WORKING-STORAGE SECTION.
       01  WS-CHOICE            PIC 9.
       01  WS-EOF               PIC X VALUE 'N'.
       01  WS-AMOUNT            PIC 9(7)V99.
       01  WS-BALANCE           PIC 9(9)V99.
       01  WS-FOUND             PIC X VALUE 'N'.

       01  WS-DISPLAY-BALANCE   PIC Z,ZZZ,ZZ9.99.
       01  WS-DISPLAY-AMOUNT    PIC Z,ZZZ,ZZ9.99.

       01  WS-MESSAGE           PIC X(50).

       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM INIT-PARA
           PERFORM MENU-PARA
           PERFORM EXIT-PARA
           STOP RUN.

       INIT-PARA.
           DISPLAY "------------------------------------"
           DISPLAY "     WELCOME TO COBOL BANK SYSTEM    "
           DISPLAY "------------------------------------".

       MENU-PARA.
           PERFORM UNTIL WS-CHOICE = 9
               DISPLAY " "
               DISPLAY "1. Deposit Amount"
               DISPLAY "2. Withdraw Amount"
               DISPLAY "3. Check Balance"
               DISPLAY "9. Exit"
               DISPLAY "Enter Choice: "
               ACCEPT WS-CHOICE

               EVALUATE WS-CHOICE
                   WHEN 1
                       PERFORM DEPOSIT-PARA
                   WHEN 2
                       PERFORM WITHDRAW-PARA
                   WHEN 3
                       PERFORM BALANCE-PARA
                   WHEN 9
                       DISPLAY "Exiting System..."
                   WHEN OTHER
                       DISPLAY "Invalid Choice"
               END-EVALUATE
           END-PERFORM.

       DEPOSIT-PARA.
           DISPLAY "Enter Account Number: "
           ACCEPT ACCT-NUMBER
           DISPLAY "Enter Deposit Amount: "
           ACCEPT WS-AMOUNT

           OPEN INPUT ACCT-FILE
           PERFORM READ-ACCOUNT
           CLOSE ACCT-FILE

           IF WS-FOUND = 'Y'
               ADD WS-AMOUNT TO ACCT-BALANCE
               MOVE ACCT-BALANCE TO WS-BALANCE
               PERFORM WRITE-ACCOUNT
               MOVE WS-BALANCE TO WS-DISPLAY-BALANCE
               DISPLAY "Updated Balance: " WS-DISPLAY-BALANCE
           ELSE
               DISPLAY "Account Not Found"
           END-IF.

       WITHDRAW-PARA.
           DISPLAY "Enter Account Number: "
           ACCEPT ACCT-NUMBER
           DISPLAY "Enter Withdraw Amount: "
           ACCEPT WS-AMOUNT

           OPEN INPUT ACCT-FILE
           PERFORM READ-ACCOUNT
           CLOSE ACCT-FILE

           IF WS-FOUND = 'Y'
               IF ACCT-BALANCE >= WS-AMOUNT
                   SUBTRACT WS-AMOUNT FROM ACCT-BALANCE
                   MOVE ACCT-BALANCE TO WS-BALANCE
                   PERFORM WRITE-ACCOUNT
                   MOVE WS-BALANCE TO WS-DISPLAY-BALANCE
                   DISPLAY "Remaining Balance: " WS-DISPLAY-BALANCE
               ELSE
                   DISPLAY "Insufficient Funds"
               END-IF
           ELSE
               DISPLAY "Account Not Found"
           END-IF.

       BALANCE-PARA.
           DISPLAY "Enter Account Number: "
           ACCEPT ACCT-NUMBER

           OPEN INPUT ACCT-FILE
           PERFORM READ-ACCOUNT
           CLOSE ACCT-FILE

           IF WS-FOUND = 'Y'
               MOVE ACCT-BALANCE TO WS-DISPLAY-BALANCE
               DISPLAY "Current Balance: " WS-DISPLAY-BALANCE
           ELSE
               DISPLAY "Account Not Found"
           END-IF.

       READ-ACCOUNT.
           MOVE 'N' TO WS-FOUND
           MOVE 'N' TO WS-EOF

           PERFORM UNTIL WS-EOF = 'Y'
               READ ACCT-FILE
                   AT END
                       MOVE 'Y' TO WS-EOF
                   NOT AT END
                       IF ACCT-NUMBER = ACCT-NUMBER
                           MOVE 'Y' TO WS-FOUND
                           MOVE 'Y' TO WS-EOF
                       END-IF
               END-READ
           END-PERFORM.

       WRITE-ACCOUNT.
           OPEN OUTPUT ACCT-FILE
           WRITE ACCT-RECORD
           CLOSE ACCT-FILE.

       EXIT-PARA.
           DISPLAY "------------------------------------"
           DISPLAY " THANK YOU FOR USING COBOL BANK APP "
           DISPLAY "------------------------------------".
