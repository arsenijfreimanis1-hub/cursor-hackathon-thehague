// BMW E46 2.8L M52TU — Drift exhaust with X-pipe & butterfly valves
// Parametric OpenSCAD source — render to STL for fabrication reference
//
// Sound target: deep, menacing — 3" primaries, X crossover, resonator delete,
// straight-through mufflers, 4" rolled tips, valves open (drift mode).

$fn = 48;

// --- Parameters (mm) ---
runner_od     = 50.8;   // 2"
primary_od    = 76.2;   // 3"
tip_od        = 101.6;  // 4"
bank_spacing  = 380;
runner_space  = 62;
x_angle       = 55;
muffler_len   = 320;
muffler_od    = 130;
valve_od      = 95;

module pipe(l, od) {
  cylinder(h = l, r = od / 2, center = true);
}

module rolled_tip(len, od, yaw_deg) {
  rotate([0, 0, yaw_deg])
    rotate([0, 18, 0])
      pipe(len, od);
}

module butterfly_valve(od, open_deg) {
  difference() {
    cylinder(h = od * 0.7, r = valve_od / 2, center = true);
    cylinder(h = od * 0.8, r = od / 2 - 1, center = true);
  }
  rotate([open_deg, 0, 0])
    cube([od - 2, 2, od * 0.85], center = true);
  translate([0, valve_od / 2 + 30, 0])
    cylinder(h = 60, r = 26, center = true);
}

module muffler(len, od, core_od) {
  difference() {
    pipe(len, od);
    pipe(len * 0.95, core_od);
  }
}

module header_bank(y_sign) {
  y0 = y_sign * bank_spacing / 2;
  for (z = [-runner_space, 0, runner_space]) {
  translate([0, y0 + z * 0.1, z])
    rotate([0, -atan2(z, 120), 0])
      pipe(140, runner_od);
  }
  translate([120, y0, 0]) sphere(r = runner_od / 2 + 2);
  translate([-20, y0, 0]) cylinder(h = 8, r = 44, center = true);
}

module primary_run(y_sign) {
  y0 = y_sign * bank_spacing / 2;
  pts = [
    [120, y0, 0],
    [300, y0, 0],
    [440, y0 * 0.35, y_sign * 25],
    [580, y0, 0]
  ];
  for (i = [0 : len(pts) - 2]) {
    p1 = pts[i];
    p2 = pts[i + 1];
    v = [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]];
    len = norm(v);
    translate(p1)
      rotate(a = [0, -atan2(v[2], v[0]), atan2(v[1], v[0])])
        pipe(len, primary_od);
  }
}

module x_crossover() {
  x0 = 440;
  len = 180;
  ang = x_angle;
  // Crossing pipes
  hull() {
    translate([x0, bank_spacing / 2, 20]) sphere(r = primary_od / 2);
    translate([x0 + len * cos(ang), -bank_spacing / 2, -20]) sphere(r = primary_od / 2);
  }
  hull() {
    translate([x0, -bank_spacing / 2, 20]) sphere(r = primary_od / 2);
    translate([x0 + len * cos(ang), bank_spacing / 2, -20]) sphere(r = primary_od / 2);
  }
  translate([x0 + len * cos(ang) / 2, 0, 0]) sphere(r = primary_od * 0.45);
}

module rear_half(y_sign) {
  y0 = y_sign * bank_spacing / 2;
  x_pipe_end = 580;
  translate([x_pipe_end, y0, 0]) pipe(80, primary_od);
  translate([x_pipe_end + 80, y0, 0]) butterfly_valve(primary_od, 88);
  translate([x_pipe_end + 150, y0, 0]) pipe(40, primary_od);
  translate([x_pipe_end + 190 + muffler_len / 2, y0, 0]) muffler(muffler_len, muffler_od, primary_od);
  translate([x_pipe_end + 190 + muffler_len + 70, y0, 0])
    rolled_tip(140, tip_od, y_sign * 15);
}

// --- Assembly ---
header_bank(1);
header_bank(-1);
primary_run(1);
primary_run(-1);
x_crossover();
rear_half(1);
rear_half(-1);
