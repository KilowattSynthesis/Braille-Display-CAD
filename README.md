# Braille-Display-CAD

Experimental design for a braille display using build123d CAD in Python

## BOM

* M2 bolts
* 4mm x 8mm DC Motors: https://www.aliexpress.com/item/1005004370822475.html

## Ideas

* Investigate bi-metallic strip with actuator.
* Investigate shape memory alloy (SMA) approach. Benefit: Would be very quiet.
* Should buy some 4mm solenoids.

* Instead of rack and pinion mask, what about laser printer fuser-like roller mask?
    * Branch: `pogo-spools`

* Key and lock mechanism pushes up on the pins

* Use Mouser's "RF Inductors" selection, mounting an inductor vertically.
    * Branch: `inductor-smd-vertical`, `inductor-smd-flat`
    * Eaton makes good-looking ones. 3225 metric (1210 imp) is too big; 2520 metric (1008 imp) might be okay. 2012 metric (0805 imp) is great!
    * "Power Inductors - Leaded" are never small enough.
    * Filter to >= 20uH inductance. Filter to >=70 mA.

    * Examples (Vertical-Mount):
        * BWLD00241715 -> Not stocked in smaller quantities, though.
            * 2.4 mm x 1.72 mm x 1.52 mm
        * LBR2012T470M -> 0805 imp (2012 metric). 47uH. 75mA rated max.

    * Examples (Horizontal-Mount):
        * VLS201612CX-220M-1 -> 22uF, very good, but shielded.


* Use GT2 belt (or similar) to press up on pins.
    * T2.5 belt is probably best - https://www.aliexpress.com/item/1005004668423141.html
    * Could try to TPU 3D print belt with the perfect braille pattern, in a closed loop. Teeth on the inside, and pattern on the outside.
    * Spring pushing on pogo pin flange, on solenoid-relieved cell frame.

* Use CNC plotter to turn pins/bolts for placement. Use hex drive, plus solenoid to mate/un-mate. Build the plotter on a PCB with 3mm linear rails, belts, etc.
    * Bolt options - Search "M2 plunger"

* Motors mounted on orthogonal PCBs, with rotating slanted plate to push on the pins.
    * Use magnets as the mating, somehow.

* Use CNC plotter to manipulate a silicone sheet which can pop up and down.

* Microfluidics as valves.

### Tested Ideas

* 4mm x 4mm x 3mm 33uH coil-wound SMD power inductor (ASPI-4030S-330M-T) can point a magnet. Magnets stick to the inductor always though.
