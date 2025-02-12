; N76E003 LCD_Pushbuttons.asm: Reads muxed push buttons using one input

$NOLIST
$MODN76E003
$LIST

;  N76E003 pinout:
;                               -------
;       PWM2/IC6/T0/AIN4/P0.5 -|1    20|- P0.4/AIN5/STADC/PWM3/IC3
;               TXD/AIN3/P0.6 -|2    19|- P0.3/PWM5/IC5/AIN6
;               RXD/AIN2/P0.7 -|3    18|- P0.2/ICPCK/OCDCK/RXD_1/[SCL]
;                    RST/P2.0 -|4    17|- P0.1/PWM4/IC4/MISO
;        INT0/OSCIN/AIN1/P3.0 -|5    16|- P0.0/PWM3/IC3/MOSI/T1
;              INT1/AIN0/P1.7 -|6    15|- P1.0/PWM2/IC2/SPCLK
;                         GND -|7    14|- P1.1/PWM1/IC1/AIN7/CLO
;[SDA]/TXD_1/ICPDA/OCDDA/P1.6 -|8    13|- P1.2/PWM0/IC0
;                         VDD -|9    12|- P1.3/SCL/[STADC]
;            PWM5/IC7/SS/P1.5 -|10   11|- P1.4/SDA/FB/PWM1
;                               -------
;

CLK               EQU 16600000 ; Microcontroller system frequency in Hz
BAUD              EQU 115200 ; Baud rate of UART in bps
TIMER1_RELOAD     EQU (0x100-(CLK/(16*BAUD)))
TIMER0_RELOAD_1MS EQU (0x10000-(CLK/1000))
TIMER2_RATE EQU 100 ; 100Hz or 10ms
TIMER2_RELOAD EQU (65536-(CLK/(16*TIMER2_RATE))) ; Need to change timer 2 input divide to 16 in T2MOD

ORG 0x0000
	ljmp main
org 0x0023
	reti
	; Timer/Counter 2 overflow interrupt vector
org 0x002B
	ljmp Timer2_ISR

START_BUTTON  equ P1.7
PWM_OUT equ P1.0 ;logic 1 = oven on
CONVERT equ P1.6


;                   1234567890123456    <- This helps determine the location of the counter
soak_param: db     'Soak: xxs xxxC', 0
reflow_param:db    'Reflow: xxs xxxC', 0
heating_to_s:  db   'Ts:xxxC To:xxxC', 0
heating_temp:db    'Temp:', 0
blank: db          '                ', 0 
safety_message:db  'ERROR: ', 0
safety_message1:db  'Cant Read Temp'
soaking:db         'Soaking time:', 0
reflow:db          'Reflow Time:',0
time:db            'Time:xxs',0
heating_to_r:db    'Tr:xxxC To:xxxC', 0
cooling:db         'Cooling down...', 0
done:db            'Done',0
ready:db           'Ready to touch',0
celsius:           'C',0
fahrenheit:        'F',0
blank_unit:        ' ',0

cseg
; These 'equ' must match the hardware wiring
LCD_RS equ P1.3
LCD_E  equ P1.4
LCD_D4 equ P0.0
LCD_D5 equ P0.1
LCD_D6 equ P0.2
LCD_D7 equ P0.3
;ADC_pn equ P1.1


$NOLIST
$include(LCD_4bit.inc) ; A library of LCD related functions and utility macros
$LIST

DSEG at 30h
STATE: ds 1
Soak_time: ds 1
Soak_temp: ds 1
soak_temp_hund: ds 1
Reflow_time: ds 1
Reflow_temp: ds 1
current_temp: ds 1
current_temp_hund: ds 1
outside_temp: ds 1
seconds: ds 1 ;seconds counter attached to timer 2 ISR
pwm_counter: ds 1 ; Free running counter 0, 1, 2, ..., 100, 0
pwm: ds 1 ; pwm percentage
reflow_temp_100:ds 1
x: ds 4
y: ds 4
z: ds 4
bcd: ds 5


BSEG
; These five bit variables store the value of the pushbuttons after calling 'LCD_PB' below
PB0: dbit 1
PB1: dbit 1
PB2: dbit 1
PB3: dbit 1
PB4: dbit 1
decrement1: dbit 1
s_flag: dbit 1 ; set to 1 every time a second has passed
mf: dbit 1
temp_flag: dbit 1
fahrenheit: dbit 1

$NOLIST
$include(math32.inc)
$LIST

CSEG

Init_All:
	; Configure all the pins for biderectional I/O
	mov	P3M1, #0x00
	mov	P3M2, #0x00
	mov	P1M1, #0x00
	mov	P1M2, #0x00
	mov	P0M1, #0x00
	mov	P0M2, #0x00
	
	orl	CKCON, #0x10 ; CLK is the input for timer 1
	orl	PCON, #0x80 ; Bit SMOD=1, double baud rate
	mov	SCON, #0x52
	anl	T3CON, #0b11011111
	anl	TMOD, #0x0F ; Clear the configuration bits for timer 1
	orl	TMOD, #0x20 ; Timer 1 Mode 2
	mov	TH1, #TIMER1_RELOAD ; TH1=TIMER1_RELOAD;
	setb TR1
	
	; Using timer 0 for delay functions.  Initialize here:
	clr	TR0 ; Stop timer 0
	orl	CKCON,#0x08 ; CLK is the input for timer 0
	anl	TMOD,#0xF0 ; Clear the configuration bits for timer 0
	orl	TMOD,#0x01 ; Timer 0 in Mode 1: 16-bit timer

	; Initialize timer 2 for periodic interrupts
	mov T2CON, #0 ; Stop timer/counter. Autoreload mode.
	mov TH2, #high(TIMER2_RELOAD)
	mov TL2, #low(TIMER2_RELOAD)
	; Set the reload value
	mov T2MOD, #0b1010_0000 ; Enable timer 2 autoreload, and clock divider is 16
	mov RCMP2H, #high(TIMER2_RELOAD)
	mov RCMP2L, #low(TIMER2_RELOAD)
	; Init the free running 10 ms counter to zero
	mov pwm_counter, #0
	; Enable the timer and interrupts
	orl EIE, #0x80 ; Enable timer 2 interrupt ET2=1
	setb TR2 ; Enable timer 2
	setb EA ; Enable global interrupts

	; Initialize the pin used by the ADC-LM335 (P1.1) as input.
	orl	P1M1, #0b00000010
	anl	P1M2, #0b11111101
	
    ;initialize the pint used by ADC-opamp output as input pin 1 (P0.5) AIN4
    orl	P0M1, #0b00010000
	anl	P0M2, #0b11101111
	

	; Initialize and start the ADC-LM335:
	;do these two when you are going to read from pin 14
    ;anl ADCCON0, #0xF0
	;orl ADCCON0, #0x07 ; Select channel 7
	
    ; AINDIDS select if some pins are analog inputs or digital I/O:
	mov AINDIDS, #0x00 ; Disable all analog inputs
	orl AINDIDS, #0b10010000 ; P1.1 and P0.5 is analog input
	orl ADCCON1, #0x01 ; Enable ADC


ret
	
wait_1ms:
	clr	TR0 ; Stop timer 0
	clr	TF0 ; Clear overflow flag
	mov	TH0, #high(TIMER0_RELOAD_1MS)
	mov	TL0,#low(TIMER0_RELOAD_1MS)
	setb TR0
	jnb	TF0, $ ; Wait for overflow
	ret

; Wait the number of miliseconds in R2
waitms:
	lcall wait_1ms
	djnz R2, waitms
	ret

Timer2_ISR:
	clr TF2 ; Timer 2 doesn't clear TF2 automatically. Do it in the ISR. It is bit addressable.
	push psw
	push acc

	inc pwm_counter
	clr c
	mov a, pwm
	subb a, pwm_counter ; If pwm_counter <= pwm then c=1
	cpl c
	mov PWM_OUT, c

	mov a, pwm_counter
	cjne a, #100, Timer2_ISR_done
	mov pwm_counter, #0
	inc seconds ; It is super easy to keep a seconds count here
	setb s_flag

Timer2_ISR_done:
	pop acc
	pop psw
	reti

LCD_PB:
	; Set variables to 1: 'no push button pressed'
	setb PB0
	setb PB1
	setb PB2
	setb PB3
	setb PB4
	; The input pin used to check set to '1'
	setb P1.5
	
	; Check if any push button is pressed
	clr P0.0
	clr P0.1
	clr P0.2
	clr P0.3
	clr P1.3
	jb P1.5, LCD_PB_Done

	; Debounce
	jb P1.5, LCD_PB_Done
	Wait_Milli_Seconds(#50)
	jb P1.5, LCD_PB_Done
	jb P1.5, $

	; Set the LCD data pins to logic 1
	setb P0.0
	setb P0.1
	setb P0.2
	setb P0.3
	setb P1.3
	
	; Check the push buttons one by one
	clr P1.3
	mov c, P1.5
	mov PB4, c
	setb P1.3

	clr P0.0
	mov c, P1.5
	mov PB3, c
	setb P0.0
	
	clr P0.1
	mov c, P1.5
	mov PB2, c
	setb P0.1
	
	clr P0.2
	mov c, P1.5
	mov PB1, c
	setb P0.2
	
	clr P0.3
	mov c, P1.5
	mov PB0, c
	setb P0.3

LCD_PB_Done:		
	ret

check_decrement: 
	jb PB0, check_stime
	cpl decrement1
	ljmp check_stime

check_stime:
	jb PB2, check_stemp
	jb decrement1, Soak_time_decrement
	mov a, Soak_time
	add a, #0x01
	da a
	mov Soak_time, a
	ljmp check_stemp

Soak_time_decrement: 
	mov a, Soak_time
	add a, #0x99
	da a
	mov Soak_time, a
	ljmp check_stemp

check_stemp:
	jb PB1, check_rtime
	jb decrement1, Soak_temp_decrement
	mov a, Soak_temp
	add a, #0x01
	da a
	mov Soak_temp, a
    cjne a, #0x99, cont_s
    ljmp add_hund_s

    cont_s:
    mov a, soak_temp_hund
	cjne a, #0x20, fini
    mov a, Soak_temp
    cjne a, #0x50, check_rtime
	mov a, #0x00
	mov Soak_temp, a
    mov a, soak_temp_hund
    mov a, #0x00
    mov soak_temp_hund, a

    fini:
	ljmp check_rtime

add_hund_s:
    mov a, soak_temp_hund
    add a, #0x10
    da A
    mov soak_temp_hund, A
    mov a, Soak_temp
    ljmp cont_s

Soak_temp_decrement: 
	mov a, Soak_temp
	add a, #0x99
	da a
	mov Soak_temp, a
    cjne a, #0x00, check_rtime
    ljmp decrement_s_hund   

    continue_dec_s:
    mov soak_temp_hund, #0x20
    mov soak_temp, #0x50
    ljmp check_rtime

    cont_s_dec:
    SUBB a, #0x10
    da A
    mov soak_temp_hund, a 
	ljmp check_rtime

decrement_s_hund:
    mov a, soak_temp_hund
    cjne a , #0x00, cont_s_dec
    ljmp continue_dec_s

check_rtime:
	jb PB4, check_rtemp 
	jb decrement1, Reflow_time_decrement
	mov a, Reflow_time
	add a, #0x01
	da a
	mov Reflow_time, a
	ljmp check_rtemp

Reflow_time_decrement: 
	mov a, Reflow_time
	add a, #0x99
	da a
	mov Reflow_time, a
	ljmp check_rtemp

check_rtemp:
	jb PB3, skipp
	jb decrement1, Reflow_temp_decrement
	mov a, Reflow_temp
	add a, #0x01
    da a
    mov Reflow_temp, a
	cjne a, #0x99, cont_r
    ljmp add_hundreds_r

    cont_r:
    ;check hundreds
    mov a, reflow_temp_100
    cjne a, #0x20, cont_count ;make sure to check with 20 since the hundreds place value is multiplied by 10
	mov a, reflow_temp
    cjne a, #0x50, skipp
    mov a, #0x00
    mov reflow_temp, a
    mov a, reflow_temp_100
    mov a, #0x00
	mov Reflow_temp_100, a
    cont_count:
	ljmp skipp

add_hundreds_r:
    mov a, reflow_temp_100
    add a, #0x10 ;add by ten bc in display it is 2 digit numbers so instead of showing 0120 for 120 itll show 120
    da A
    mov reflow_temp_100, A
    mov a, Reflow_temp
    ljmp cont_r


Reflow_temp_decrement: 
	mov a, Reflow_temp
	add a, #0x99
	da a
	mov Reflow_temp, a
    cjne a, #0x00, skipp
    ljmp decrement_r_hund

    continue_dec_r:
	;mov a, reflow_temp
    ;cjne a, #0x00, skipp
    mov reflow_temp, #0x50
    mov reflow_temp_100, #0x20
    ljmp skipp

    cont_dec:
    SUBB a, #0x10
    da a
    mov reflow_temp_100, a
	ljmp skipp

    decrement_r_hund:
    mov a, reflow_temp_100
    cjne a, #0x00, cont_dec
    ljmp continue_dec_r

skipp:
	ret

Check_start:
	jb START_BUTTON, smjmp  ; if the 'Start' button is not pressed skip
	Wait_Milli_Seconds(#50)	; Debounce delay.  This macro is also in 'LCD_4bit.inc'
	jb  START_BUTTON, smjmp  ; if the 'Start' button is not pressed skip
	jnb START_BUTTON, $		; Wait for button release.  The '$' means: jump to same instruction.
	mov STATE, #0x01
	ret

smjmp:
ljmp skipp

wait_for_ti:
    jnb TI, wait_for_ti
    clr TI
    ret

display_menu:
	Set_Cursor(1,7) 
	Display_BCD(Soak_time)
	Set_Cursor(1,11)
	Display_BCD(Soak_temp_hund)
	set_cursor(1,12)
	display_bcd(soak_temp)
	Set_Cursor(2,9)
	Display_BCD(Reflow_time)
    set_cursor(2,13)
    display_bcd(reflow_temp_100)
	set_cursor(2,14)
    display_bcd(reflow_temp)
    ret

display_heating_s:
	;Set_Cursor(1,4)
	;Display_BCD(Soak_temp_hund)
	;set_cursor(1,5)
	;display_bcd(soak_temp)
	Set_Cursor(1,12)
	Display_BCD(outside_temp)
	Set_Cursor(2,7)
	Display_BCD(current_temp)
	ret

display_heating_r:
	;Set_Cursor(1,4)
	;Display_BCD(reflow_temp_100)
	;set_cursor(1,5)
	;display_bcd(reflow_temp)
	Set_Cursor(1,12)
	Display_BCD(outside_temp)
	Set_Cursor(2,7)
	Display_BCD(current_temp)
	ret

display_blank:
	Set_Cursor(1,1)
	Send_Constant_String(#blank)
	Set_Cursor(2,1)
	Send_Constant_String(#blank)
	ret

Display_formated_BCD:
	Set_Cursor(1, 12)
	Display_BCD(bcd+2)
	Display_char(#'.')
	Display_BCD(bcd+1)
	ret

conv_to_bcd_high:
    swap a
    anl a, #0x0f
    mov R1, a
	ret

conv_to_bcd_low:
    anl a, #0x0f
    mov R0, A
	ret

conv_to_bcd:
	mov x+0, R0
	mov x+1, R1
	mov x+2, #0
	mov x+3, #0
    lcall hex2bcd
	ret
String: 
	DB '\r', '\n', 0

Outside_tmp:
    anl ADCCON0, #0xF0
    orl ADCCON0, #0x07 ; Select channel 7 

    clr ADCF
    setb ADCS
    jnb ADCF, $

    mov a, ADCRH
    swap a
    push acc
    anl a, #0x0f
    mov R1, a
    pop acc
    anl a, #0xf0
    orl a, ADCRL
    mov R0, A
    
    ; Convert to voltage
	mov x+0, R0
	mov x+1, R1
	mov x+2, #0
	mov x+3, #0
	Load_y(50300) ; VCC voltage measured
	lcall mul32
	Load_y(4095) ; 2^12-1
	lcall div32
	Load_y(27300)
	lcall sub32
	load_y(100)
	lcall mul32
    ;save outside temp to z to later add onto the oven temp
    mov z+0, x+0
    mov z+1, x+1
    mov z+2, x+2
    mov z+3, x+3 
	jnb fahrenheit, outside_temp_continue

fahrenheit_conversion:
	load_y(9)
	lcall mul32
	load_y(5)
	lcall div32 
	load_y(32)
	lcall add32

outside_temp_continue:
    lcall hex2bcd
    mov a, STATE
    cjne a, #5, display
    ret

display:
    lcall Display_formated_BCD
    ret

oven_tmp:
    anl  ADCCON0, #0xF0  
    orl  ADCCON0, #0x04  ; Select AIN4 (P0.5)

    clr ADCF
    setb ADCS
    jnb ADCF, $

    mov a, ADCRH
    swap a
    push acc
    anl a, #0x0f
    mov R1, a
    pop acc
    anl a, #0xf0
    orl a, ADCRL
    mov R0, A
    
    ; Convert to voltage
	mov x+0, R0
	mov x+1, R1
	mov x+2, #0
	mov x+3, #0
    Load_y(50300) ; VCC voltage measured
	lcall mul32
	Load_y(4095) ; 2^12-1
	lcall div32

	;vout of opamp should now be in x
    ;use formula vout=41uV/degC * R1/R2 --> degC = (vout*R2)/41*r1
    ;first calculate vout*R2:
    load_y(1469)
    lcall mul32
    ;now vout*R2 ohm is in x
    ;next we will take 461 650V and divide
    load_y(461650) 
    lcall div32
    ;multiply by 100k and then divide by 41 to cancel units
    load_y(1000000)
    lcall mul32
    load_y(41)
    lcall div32
    ;move the outside temp to y and add
    mov y+0, z+0
    mov y+1, z+1
    mov y+2, z+2
    mov y+3, z+3
    lcall add32
    lcall hex2bcd

	Send_BCD(bcd+4)
	Send_BCD(bcd+3)
	Send_BCD(bcd+2)
	Send_BCD(bcd+1)
	Send_BCD(bcd+0)

	mov DPTR, #String
	clr A
	movc A, @A+DPTR
	lcall putchar
	inc DPTR

    mov current_temp, bcd+2
    mov current_temp_hund, bcd+3
    jnb fahrenheit, display_oven_tmp
	lcall bcd2hex
	load_y(9)
	lcall mul32
	load_y(5)
	lcall div32 
	load_y(32)
	lcall add32   
	lcall hex2bcd 

display_oven_tmp:
	Set_Cursor(2,6)
    display_bcd(bcd+3)
	Display_BCD(bcd+2)
	Display_char(#'.')
	Display_BCD(bcd+1)
	ret

skipp1:
	ret
clearx:
	mov x+0, #0x00
	mov x+1, #0x00
	mov x+2, #0x00
	mov x+3, #0x00
	ret 

check_temps:
	mov a, current_temp 
	subb a, Soak_temp ; subb sets carry flag if a borrow is needed (current_temp < soaktemp)
	;soak temp is 10 for 100, current temp is 1 for 100 
	jc skipp1 ; skip if current_temp < soak_temp (carry bit set)
	mov a, current_temp_hund
	cjne a, soak_temp_hund, next2 ; hundreds place moves relatively slowly so can we can just use cjne
	mov STATE, #0x02
next2:
	ret

check_currenttemp:
	mov a, current_temp
	subb a, #0x50
	jc skipp1
	setb temp_flag ; set safety flag if temp >=60
	ret

safety_feature:
	mov a, seconds
	cjne a, #0x3C, skipp1 ; skip if current time is not 60
	jb temp_flag, skipp2 ; skip if temperature checks passed
	lcall display_blank
	mov pwm, #0
	Set_Cursor(1,1)
	Send_Constant_String(#safety_message)
	Set_Cursor(2,1)
	Send_Constant_String(#safety_message1)

safety_feature_loop:
	ljmp safety_feature_loop

skipp2:
	ret

; checks secs for state 2 -> 3
check_secs_s2:
	mov bcd, soak_time 			; soak_time stored as bcd
	lcall bcd2hex
    mov a, x
    cjne a, seconds, skip_check_secs_s2
	;lcall debug_display
    mov state, #3
skip_check_secs_s2:
    ret

; checks temp for state 3 -> 4
check_temps_s3:
	mov a, current_temp 
	subb a, Reflow_temp
	jc skipp2
	mov a, current_temp_hund
	cjne a, reflow_temp_100, nxt2
	mov STATe, #0x04
nxt2:
	ret

; checks secs for state 4 -> 5
check_secs_s4:
	mov bcd, reflow_time ; reflow_time stored as bcd
	lcall bcd2hex
    mov a, x
    cjne a, seconds, skip_check_secs_s4
    mov state, #5
skip_check_secs_s4:
    ret

; checks temp for state 5 -> 0
check_temp_s5:
    mov a, #0x60
	subb a, current_temp
	jc skipp2
	mov a, current_temp_hund
	cjne a, #0, nx2
	mov STATE, #0x00
nx2:
	ret
ret

reset_seconds:
	mov a, seconds
	mov a, #0x00
	mov seconds, a
	;lcall clearx
	;mov x, soak_time
	;lcall bcd2hex
	;mov soak_time, x

	;mov a, seconds
	;SUBB a, soak_time
	;mov seconds, a
ret

check_convert: 
	jb CONVERT, smjmp  ; if the 'Start' button is not pressed skip
	Wait_Milli_Seconds(#50)	; Debounce delay.  This macro is also in 'LCD_4bit.inc'
	jb  CONVERT, smjmp  ; if the 'Start' button is not pressed skip
	jnb CONVERT, $		; Wait for button release.  The '$' means: jump to same instruction.
	cpl fahrenheit 
	ret 

fahrenheit_display:
	set_cursor(2,13)
	send_constant_string(#blank_unit)
	send_constant_string(#fahrenheit)
	ret 

celsius_display:
	set_cursor(2,13)
	send_constant_string(#blank_unit)
	send_constant_string(#celsius)
	ret 

main:
	mov sp, #0x7f
	lcall Init_All
    lcall LCD_4BIT
	lcall Timer2_ISR
    
     ; initial messages in LCD
    mov STATE, #0x00
    mov Soak_time, #0x00
    mov Soak_temp, #0x00
    mov soak_temp_hund, #0x00
    mov Reflow_time, #0x00
    mov Reflow_temp, #0x00
    mov current_temp, #0x00
    mov current_temp_hund, #0x00
    mov seconds, #0x00
    mov pwm_counter, #0x00
    mov pwm, #0x00
    mov reflow_temp_100, #0x00
    clr decrement1
    clr s_flag 
    clr fahrenheit
	
Forever:
	lcall display_blank

state_0:
	Set_Cursor(1, 1)
	Send_Constant_String(#soak_param)
	Set_Cursor(2, 1)
	Send_Constant_String(#reflow_param)

state_0_loop:
	mov a, STATE
        mov pwm, #100
	cjne a, #0, state_1
	lcall LCD_PB
	lcall check_decrement
	lcall display_menu
	lcall Check_start
	ljmp state_0_loop

state_1: 
	lcall display_blank
	mov seconds, #0x00
	Set_Cursor(1, 1)
	Send_Constant_String(#heating_to_s)
	Set_Cursor(2, 1)
	Send_Constant_String(#heating_temp)

	Set_Cursor(1,4)
	Display_BCD(Soak_temp_hund)
	set_cursor(1,5)
	display_bcd(soak_temp)

	lcall clearx
	mov bcd+0, #0x00
	mov bcd+1, #0x00
	mov bcd+2, #0x00
	mov bcd+3, #0x00
	mov bcd, soak_temp_hund
	lcall bcd2hex
	load_y(10)
	lcall div32
	lcall hex2bcd
	mov soak_temp_hund, bcd
	
state_1_loop:
	mov a, STATE
	cjne a, #1, state_2
	lcall display_heating_s
	mov pwm, #0
	lcall check_convert
	lcall outside_tmp
	lcall oven_tmp
	lcall check_currenttemp
	lcall safety_feature
	lcall check_temps
	jb fahrenheit, fahrenheit_display
	jnb fahrenheit, celsius_display
	mov R2, #250
	lcall waitms
	ljmp state_1_loop

state_2:
	lcall display_blank 
	mov seconds, #0
	Set_Cursor(1,1)
	Send_Constant_String(#soaking)
	Set_Cursor(2,1)
	Send_Constant_String(#time)
	Set_Cursor(1, 14)
	display_BCD(soak_time)


state_2_loop: 
	mov a, STATE
    cjne a, #2, state_3
	Set_Cursor(2,6)
	lcall clearx
	mov x, seconds 
	lcall hex2bcd 
	display_BCD(bcd)
	lcall clearx
	mov pwm, #80
	lcall check_secs_s2
	ljmp state_2_loop

state_3:
	mov seconds, #0
	lcall reset_seconds
	lcall display_blank
	Set_Cursor(1, 1)
	Send_Constant_String(#heating_to_r)
	Set_Cursor(2, 1)
	Send_Constant_String(#heating_temp)
	
	Set_Cursor(1,4)
	Display_BCD(reflow_temp_100)
	set_cursor(1,5)
	display_bcd(reflow_temp)

	lcall clearx
	mov bcd+0, #0x00
	mov bcd+1, #0x00
	mov bcd+2, #0x00
	mov bcd+3, #0x00
	mov bcd, reflow_temp_100
	lcall bcd2hex
	load_y(10)
	lcall div32
	lcall hex2bcd
	mov reflow_temp_100, bcd

state_3_loop:
	mov a, STATE
	cjne a, #3, state_4
	lcall display_heating_r
	mov pwm, #0
	lcall check_convert
	lcall outside_tmp
	lcall oven_tmp
	lcall check_temps_s3
	jb fahrenheit, fahrenheit_display
	jnb fahrenheit, celsius_display
	mov R2, #250
	lcall waitms
	ljmp state_3_loop

state_4:
	lcall display_blank
	mov seconds, #0
	Set_Cursor(1,1)
	Send_Constant_String(#reflow)
	Set_Cursor(2,1)
	Send_Constant_String(#time)
	Set_Cursor(1, 14)
	display_BCD(reflow_time)

state_4_loop:
    mov a, STATE
    cjne a, #4, state_5
    Set_Cursor(2,6)
    lcall clearx
    mov x, seconds
    lcall hex2bcd
    display_BCD(bcd)
    lcall clearx
    mov pwm, #20
    lcall check_secs_s4
    ljmp state_4_loop

state_5:
    lcall display_blank
    Set_Cursor(1,1)
    Send_Constant_String(#cooling)
    Set_Cursor(2,1)
    Send_Constant_String(#heating_temp)
    
state_5_loop:
	mov a, STATE
	cjne a, #5, state_6
	mov pwm, #100
	Set_Cursor(2,7)
	Display_BCD(current_temp)
	lcall outside_tmp
	lcall oven_tmp
	lcall check_temp_s5
	lcall check_convert
	mov R2, #250
	lcall waitms
	ljmp state_5_loop

state_6:
	lcall display_blank
	set_cursor(1,1)
	send_constant_string(#done)
	set_cursor(2,1)
	send_constant_string(#ready)
	ljmp state_6

END
