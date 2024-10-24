# Braille-Display-CAD

Experimental design for a braille display using build123d CAD in Python

## BOM

* M2 bolts
* 4mm x 8mm DC Motors: https://www.aliexpress.com/item/1005004370822475.html

## Ideas

* Investigate bi-metallic strip with actuator.
* Investigate shape memory alloy (SMA) approach. Benefit: Would be very quiet.
* Should buy some 4mm solenoids
* Instead of rack and pinion mask, what about laser printer fuser-like roller mask?
* Key and lock mechanism pushes up on the pins

* Use Mouser's "RF Inductors" selection, mounting an inductor vertically.
    * Eaton makes good-looking ones. 3225 metric (1210 imp) is too big; 2520 metric (1008 imp) might be okay. 2012 metric (0805 imp) is great!
    * "Power Inductors - Leaded" are never small enough.
    * Filter to >= 20uH inductance. Filter to >=70 mA.

    * Examples (Vertical-Mount):
        * BWLD00241715 -> Not stocked in smaller quantities, though.
            * 2.4 mm x 1.72 mm x 1.52 mm
        * LBR2012T470M -> 0805 imp (2012 metric). 47uH. 75mA rated max.

    * Examples (Horizontal-Mount):
        * VLS201612CX-220M-1 -> 22uF, very good, but shielded.
        

### Tested Ideas

* 4mm x 4mm x 3mm 33uH coil-wound SMD power inductor (ASPI-4030S-330M-T) can point a magnet. Magnets stick to the inductor always though.
