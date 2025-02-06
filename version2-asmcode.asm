state_3:
    lcall display_blank
    mov seconds, #0x00
    Set_Cursor(1,1)
    Send_Constant_String(#reflowing)
    Set_Cursor(2,1)
    Send_Constant_String(#time)
    Set_Cursor(1,14)
    display_BCD(reflow_time)

state_3_loop:
    Set_Cursor(2,6)
    display_BCD(seconds)
    mov x, seconds
    lcall hex2bcd
    display_BCD(bcd)
    mov pwm, #100
    lcall check_temps
    lcall safety_feature
    mov R2, #250
    lcall waitms
    mov R2, #250
    lcall waitms
    mov a, STATE
    cjne a, #3, state_4
    ljmp state_3_loop

state_4:
    lcall display_blank
    mov seconds, #0x00
    Set_Cursor(1,1)
    Send_Constant_String(#cooling)
    Set_Cursor(2,1)
    Send_Constant_String(#time)
    Set_Cursor(1,14)
    display_BCD(cooling_time)

state_4_loop:
    Set_Cursor(2,6)
    display_BCD(seconds)
    mov x, seconds
    lcall hex2bcd
    display_BCD(bcd)
    mov pwm, #20
    lcall check_temps
    lcall safety_feature
    mov R2, #250
    lcall waitms
    mov R2, #250
    lcall waitms
    mov a, STATE
    cjne a, #4, state_5
    ljmp state_4_loop

state_5:
    lcall display_blank
    mov seconds, #0x00
    Set_Cursor(1,1)
    Send_Constant_String(#cooldown_complete)
    Set_Cursor(2,1)
    Send_Constant_String(#ready_to_open)
    
state_5_loop:
    mov pwm, #0
    lcall safety_feature
    lcall display_ready
    mov a, STATE
    cjne a, #5, state_0
    ljmp state_5_loop

END
