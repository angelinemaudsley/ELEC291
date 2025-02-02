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

START_BUTTON  equ P1.7
PWM_OUT equ P1.0 ;logic 1 = oven on


;                1234567890123456    <- This helps determine the location of the counter
soak_param: db  'Soak: xxs xxxC', 0
reflow_param:db 'Reflow: xxs xxxC', 0
heating_to:  db 'Ts:xxxC To:xxxC', 0
heating_temp:db 'Temp: xxxC', 0
blank: db       '                ', 0     

cseg
; These 'equ' must match the hardware wiring
LCD_RS equ P1.3
LCD_E  equ P1.4
LCD_D4 equ P0.0
LCD_D5 equ P0.1
LCD_D6 equ P0.2
LCD_D7 equ P0.3
ADC_pn equ P1.1

$NOLIST
$include(LCD_4bit.inc) ; A library of LCD related functions and utility macros
$LIST

DSEG at 0x30
STATE: ds 1
Soak_time: ds 1
Soak_temp: ds 1
Reflow_time: ds 1
Reflow_temp: ds 1
current_temp: ds 1
outside_temp: ds 1
seconds: ds 1 ;seconds counter attached to timer 2 ISR
pwm_counter: ds 1 ; Free running counter 0, 1, 2, ..., 100, 0
pwm: ds 1 ; pwm percentage
x: ds 4
y: ds 4
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

$NOLIST
$include(math32.inc)
$LIST

CSEG
ORG 0x0000
	ljmp main
org 0x0023
	reti
	; Timer/Counter 2 overflow interrupt vector
org 0x002B
	ljmp Timer2_ISR

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

	; Initialize the pin used by the ADC (P1.1) as input.
	orl	P1M1, #0b00000010
	anl	P1M2, #0b11111101
	
	; Initialize and start the ADC:
	anl ADCCON0, #0xF0
	orl ADCCON0, #0x07 ; Select channel 7
	; AINDIDS select if some pins are analog inputs or digital I/O:
	mov AINDIDS, #0x00 ; Disable all analog inputs
	orl AINDIDS, #0b10000000 ; P1.1 is analog input
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
	clr TF2 ; Timer 2 doesn't clear TF2 automatically. Do it in the ISR. It is
	bit addressable.
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
	mov R2, #50
	lcall waitms
	jb P1.5, LCD_PB_Done

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
	jb PB1, check_stemp
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
	jb PB2, check_rtime
	jb decrement1, Soak_temp_decrement
	mov a, Soak_temp
	add a, #0x01
	da a
	mov Soak_temp, a
	cjne a, #250, check_rtime
	mov a, #0x00
	mov Soak_temp, a
	ljmp check_rtime

Soak_temp_decrement: 
	mov a, Soak_temp
	add a, #0x99
	da a
	mov Soak_temp, a
	cjne a, #250, check_rtime
	mov a, #0x00
	mov Soak_temp, a
	ljmp check_rtime

check_rtime:
	jb PB3, check_rtemp 
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
	jb PB4, skipp
	jb decrement1, Reflow_temp_decrement
	mov a, Reflow_temp
	add a, #0x01
	da a
	mov Reflow_temp, a
	cjne a, #250, skipp
	mov a, #0x00
	mov Reflow_temp, a
	ljmp skipp

Reflow_temp_decrement: 
	mov a, Reflow_temp
	add a, #0x99
	da a
	mov Reflow_temp, a
	cjne a, #250, skipp
	mov a, #0x00
	mov Reflow_temp, a
	ljmp skipp

skipp:
	ret

Check_start:
	jb START_BUTTON, smjmp  ; if the 'Start' button is not pressed skip
	Wait_Milli_Seconds(#50)	; Debounce delay.  This macro is also in 'LCD_4bit.inc'
	jb  START_BUTTON, smjmp  ; if the 'Start' button is not pressed skip
	jnb START_BUTTON, $		; Wait for button release.  The '$' means: jump to same instruction.
	mov STATE, #0x01
	ret
sjmp:
ljmp skipp

wait_for_ti:
    jnb TI, wait_for_ti
    clr TI
    ret

display_menu:
	Set_Cursor(1,7) 
	Display_BCD(Soak_time)
	Set_Cursor(1,11)
	Display_BCD3(Soak_temp)
	Set_Cursor(2,9)
	Display_BCD(Reflow_time)
	Set_Cursor(2,13)
	Display_BCD3(Reflow_temp)
	ret

display_heating:
	Set_Cursor(1, 1)
	Send_Constant_String(#heating_to)
	Set_Cursor(2, 1)
	Send_Constant_String(#heating_temp)
	Set_Cursor(1,4)
	Display_BCD(Soak_temp)
	Set_Cursor(1,12)
	Display_BCD(outside_temp)
	Set_Cursor(2,7)
	Display_BCD(current_temp)
	ret

display_blank:
	Set_Cursor(1,1)
	Send_Constant_String(#blank)
	ret

Display_formated_BCD:
	Set_Cursor(1, 12)
	Display_BCD(bcd+2)
	Display_char(#'.')
	Display_BCD(bcd+1)
	Display_BCD(bcd+0)
	Set_Cursor(2, 10)
	;Display_char(#'=')
	ret

Outside_tmp:
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

    lcall hex2bcd
    lcall Display_formated_BCD
	
	ret

main:
	mov sp, #0x7f
	lcall Init_All
    lcall LCD_4BIT
    
     ; initial messages in LCD
	Set_Cursor(1, 1)
    Send_Constant_String(#soak_param)
	Set_Cursor(2, 1)
    Send_Constant_String(#reflow_param)
    mov STATE, #0x00
    mov Soak_time, #0x00
    mov Soak_temp, #0x00
    mov Reflow_time, #0x00
    mov Reflow_temp, #0x00
    mov current_temp, #0x00
    mov seconds, #0x00
    mov pwm_counter, #0x00
    mov pwm, #0x00
    clr decrement1
    clr s_flag 
	
Forever:
	
	state_0: 
	lcall display_blank
	mov a, STATE
        mov pwm, #0
	cjne a, #0, state_1
	lcall LCD_PB
	lcall check_decrement
	lcall display_menu
	lcall Check_start
	ljmp state_0

	state_1: 
	lcall display_blank
	lcall display_heating
	mov pwm, #100
	lcall outside_tmp
	ljmp Forever
	
END
	
