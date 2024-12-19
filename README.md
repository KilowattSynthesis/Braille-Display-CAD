# Braille-Display-CAD

Experimental design for a braille display using build123d CAD in Python

## Interesting Parts

* 4mm x 8mm DC Motors: https://www.aliexpress.com/item/1005004370822475.html
* 2.8mm x 3.9mm DC Motors: https://www.aliexpress.com/item/1005006897190118.html

## Explored Ideas

### Pogo Spools

* Laser printer fuser-like roller mask.
    * Branch: `archive/pogo-spools`
    * Files: `ideas_pogo_spool_mask/`
* Made PCB with small stepper motors, tiny CAD parts (spools).

### RF Inductors as Electromagnets

* Use Mouser's "RF Inductors" selection, mounting an inductor vertically.
    * Branches: `archive/inductor-smd-vertical`, `archive/inductor-smd-flat`
    * Eaton makes good-looking ones. 3225 metric (1210 imp) is too big; 2520 metric (1008 imp) might be okay. 2012 metric (0805 imp) is great!
    * "Power Inductors - Leaded" are never small enough.
    * Filter to >= 20uH inductance. Filter to >=70 mA.
    * Examples (Vertical-Mount):
        * BWLD00241715 -> Not stocked in smaller quantities, though.
            * 2.4 mm x 1.72 mm x 1.52 mm
        * LBR2012T470M -> 0805 imp (2012 metric). 47uH. 75mA rated max.
    * Examples (Horizontal-Mount):
        * VLS201612CX-220M-1 -> 22uF, very good, but shielded.

* Test results:
    * 4mm x 4mm x 3mm 33uH coil-wound SMD power inductor (ASPI-4030S-330M-T) can point a magnet. Magnets stick to the inductor always though.
    * Several inductors, up to 6mm diameter (and 1-2 MH), with 24V get very hot, but don't levitate a 1mm or 2mm neodymium magnet.
        * Good at pointing pointing the magnet, if it starts far away.
        * Cannot remove the magnet from the inductor once it's stuck.

* **Conclusion**: RF inductors don't have enough magnetic force to levitate 1mm or 2mm neodymium magnets.

### Nut/Bolt Grid

* Turn a bolt in a threaded hole/nut. Each bolt is a dot. User directly touches the dot.
* Movement can be done with one motor per dot (very tiny motors, maybe stacked), or motors can be moved between dots (CNC plotter style). Multiple heads can be used.
* Branch: `archive/cnc-plotter`
* Files: `cad/nut_bolt_grid.py`, `cad/vertical_motor_layers.py`


### Silicone Sheet

* Use CNC plotter to manipulate a silicone sheet which can pop up and down.
    * Branch: `archive/silicone-sheet`
    * Files: `cad/silicone_sheet_mold/`

## Unexplored/Unrealized Ideas

* Investigate bi-metallic strip with actuator.
* Investigate shape memory alloy (SMA) approach. Benefit: Would be very quiet.
* Should buy some 4mm solenoids.

* Key and lock mechanism pushes up on the pins

* Use GT2 belt (or similar) to press up on pins.
    * T2.5 belt is probably best - https://www.aliexpress.com/item/1005004668423141.html
    * Could try to TPU 3D print belt with the perfect braille pattern, in a closed loop. Teeth on the inside, and pattern on the outside.
    * Spring pushing on pogo pin flange, on solenoid-relieved cell frame.

* Use CNC plotter to turn pins/bolts for placement. Use hex drive, plus solenoid to mate/un-mate. Build the plotter on a PCB with 3mm linear rails, belts, etc.
    * Branch: `cnc-plotter`
    * Bolt options - Search "M2.5 plunger"
    * Best option: M1.6 Grub Screw, probably.
    * Create top plate with Z-stacked nuts on it.
    * Screw driver or nut will move up and down and turn screws.
    * Search "Micro Linear Motor" for gantry.
    * Focus on M1.6 and M2.5 designs.
    * To move the screw:
        * Use a spring to push the bit up, and a solenoid to pull it down.
        * Use a hex bit maybe, or use rubber friction.
    * BOM:
        * LM3UU linear bearings (ID=3mm, OD=7mm, L=10mm)
        * 3mm Rod x 100mm
        * PM15S Stepper Motors: https://www.aliexpress.com/item/1005005152436475.html
        * GT2 belt
        * GT2 pulley, custom to mate with stepper motor's gear.

* Motors mounted on orthogonal PCBs, with rotating slanted plate to push on the pins.
    * Use magnets as the mating, somehow.

* Microfluidics as valves.

* MEMS on-chip stepper motor:
    * https://www.youtube.com/watch?v=n3YMjgbhvTA
    * Could be useful to drive the screws on the CNC Plotter style.

* Double screw with balls and weird geometry.

* Cams on 2.4mm diameter rods that run along each column of dots.
    * Each cam would have 8 positions, so 45 degrees per position.
    * Would probably need to move table up-and-down independently of the cams.
    * One motor per cam, probably.
    