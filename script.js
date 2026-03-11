// ===================================================================
// CRICSHOT·AI — Frontend Script
// ===================================================================

// API base — empty string = same origin (always use Flask at port 5000)
// If you see reload issues, make sure to open http://localhost:5000 NOT http://localhost:5500
const API_BASE = window.location.port === "5000" || window.location.port === ""
  ? ""
  : "http://localhost:5000";

// Show wrong-port banner if not on port 5000
if (window.location.port && window.location.port !== "5000") {
  const banner = document.getElementById("wrong-port-banner");
  if (banner) banner.style.display = "flex";
}

// ─── Shot Metadata ─────────────────────────────────────────────────
const SHOT_META = {
  "Cover Drive": { emoji: "🏏", desc: "An elegant off-side drive played with a straight bat through the covers." },
  "Defensive": { emoji: "🛡️", desc: "A dead-bat shot played close to the body to protect the wicket." },
  "Down The Wicket": { emoji: "🦶", desc: "Batsman advances down the pitch to meet the ball, typically against spin." },
  "Flick": { emoji: "💨", desc: "A wristy leg-side shot guiding the ball fine or square off the pads." },
  "Hook": { emoji: "🔄", desc: "An aggressive cross-bat shot to a short-pitched ball at head height." },
  "Late Cut": { emoji: "✂️", desc: "A delicate shot played late behind square on the off side." },
  "Lofted Legside": { emoji: "🚀", desc: "An attacking lofted hit over the leg-side boundary." },
  "Lofted Offside": { emoji: "🌟", desc: "A powerful lofted drive launched over off-side fielders." },
  "Pull": { emoji: "💪", desc: "A strong cross-bat shot to a short delivery at chest height." },
  "Reverse Sweep": { emoji: "🔃", desc: "An unorthodox sweep to the off side with a reversed grip." },
  "Scoop": { emoji: "🥄", desc: "A cheeky scoop over the wicketkeeper's head towards fine leg." },
  "Square Cut": { emoji: "📐", desc: "A horizontal-bat cut to a short, wide delivery outside off stump." },
  "Straight Drive": { emoji: "➡️", desc: "The purest shot in cricket — hit back past the bowler along the ground." },
  "Sweep": { emoji: "🧹", desc: "A cross-bat sweep to a good-length delivery on leg stump." },
  "Upper Cut": { emoji: "☝️", desc: "A shot slapping a short, wide ball above shoulder height over third man." },
  "drive": { emoji: "💥", desc: "A classical front-foot drive along the ground on the off or on side." },
  "legglance-flick": { emoji: "🔮", desc: "A wristy glance guiding the ball fine on the leg side off the hip." },
  "pullshot": { emoji: "🎯", desc: "A forceful pull sending a short-pitched ball to mid-wicket or square leg." }
};

// ─── Detailed Shot Info (for modal) ────────────────────────────────
const SHOT_DETAIL = {
  "Cover Drive": {
    tag: "Attacking · Off Side · Front Foot",
    facts: [{ label: "Direction", val: "Cover / Extra Cover" }, { label: "Foot", val: "Front Foot" }, { label: "Bat swing", val: "Straight / V-shaped" }, { label: "Difficulty", val: "Intermediate" }],
    youtube: "how to play cover drive cricket batting tutorial",
    body: [
      "The cover drive is widely considered the most aesthetically beautiful shot in cricket. It is played to a full-pitched or good-length delivery angled towards the off stump, driving the ball through the gap between cover and extra cover.",
      "The batsman moves the front foot to the pitch of the ball, keeps the head still and eyes level, and swings the bat in a straight, downward arc. The wrists roll over at impact to keep the ball on the ground.",
      "It requires impeccable timing rather than brute force. Players like Sachin Tendulkar, Brian Lara, and Virat Kohli have made this shot their signature, often hitting it with such precision that no fielder can intercept it.",
      "The shot is particularly effective when the ball is pitched on or outside off stump at a full length. It becomes risky against late swing or away movement that can take the edge to the slip cordon."
    ],
    tips: ["Drive the ball — don't swing at it; let the ball come to you.", "Head over the front knee at impact keeps the ball on the ground.", "Follow-through high and towards your target for maximum control.", "Watch the ball all the way onto the bat face."]
  },
  "Defensive": {
    tag: "Defensive · Both Sides · Front & Back Foot",
    facts: [{ label: "Purpose", val: "Survival / Occupation" }, { label: "Risk", val: "Very Low" }, { label: "Bat angle", val: "Angled Down" }, { label: "Used against", val: "All bowling types" }],
    youtube: "how to play forward defense cricket blocking shot tutorial",
    body: [
      "The defensive shot is the foundation of all batting. It is played with a soft, dead bat to present no chance of an attacking shot and to protect the wicket when conditions are difficult or the ball is doing too much.",
      "The front-foot defensive is used to a full delivery: the leading foot strides to the pitch of the ball, the bat angle is pushed slightly down and forward, and the wrists are softened so the ball drops at the batsman's feet.",
      "The back-foot defensive is used to a good-length or short-of-a-length ball: the weight transfers onto the back foot, and the bat is angled down to keep the ball away from the slip cordon.",
      "Elite batsmen use the defensive shot not just to survive, but as a psychological tool — showing patience to tire out the bowler before launching an attack in favourable conditions.",
      "The shot requires intense focus on the ball's seam position, trajectory, and any swing or spin. Eliminating the drive impulse is often the hardest mental challenge for young cricketers."
    ],
    tips: ["Keep the elbow of the top hand high to create a downward bat angle.", "Soft hands — let the ball die in front of you, don't push.", "Watch the seam all the way to the bat face.", "Stay balanced on both feet; avoid lunging."]
  },
  "Down The Wicket": {
    tag: "Attacking · Skip · Spin Countering",
    facts: [{ label: "Target", val: "Spin bowling" }, { label: "Foot movement", val: "Large stride forward" }, { label: "Aim", val: "Negate turn / loft" }, { label: "Risk", val: "Stumping if missed" }],
    youtube: "how to go down the wicket against spin cricket batting tutorial",
    body: [
      "Going 'down the wicket' means advancing towards the bowler by taking quick steps down the pitch before the ball arrives, with the goal of reaching the pitch of the ball and eliminating the turn that a spinner can extract.",
      "By meeting the ball at the top of its bounce before it can deviate, the batsman can either drive it powerfully along the ground or loft it over the infield when the spinner pushes it through flatter.",
      "This is primarily a tactic against spin bowling — pacemen rarely allow this because of sheer speed. It was famously used by batsmen like MS Dhoni and Adam Gilchrist to disrupt a spinner's rhythm.",
      "The biggest risk is being stumped: if the batsman misses and the wicketkeeper collects the ball quickly, he may be far outside the crease. Quick footwork, a still head, and firm commitment are essential.",
      "Reading the bowler's hand position, flight, and dip is crucial. Misreading an arm ball or a straighter one can lead to a dismissal bowled or lbw."
    ],
    tips: ["Commit fully — hesitation leads to being stranded mid-pitch.", "Use the crease to time your charge to the pitch of the ball.", "Keep head down and eyes on the ball through the stroke.", "Have a plan B — if the ball is too short, abort and go back."]
  },
  "Flick": {
    tag: "Attacking · Leg Side · Wristy",
    facts: [{ label: "Direction", val: "Fine Leg / Mid-Wicket" }, { label: "Foot", val: "Front Foot" }, { label: "Key skill", val: "Wrist rotation" }, { label: "Delivery", val: "Full, into pads" }],
    youtube: "how to play flick shot cricket wrist leg side tutorial",
    body: [
      "The flick is a compact, wristy shot played to a full delivery aimed at or around the leg stump or into the body. Instead of defending, the batsman uses the wrists to deflect the ball to the leg side.",
      "The stroke is played off the front foot with minimal back-lift. The key is to use the wrists at the point of contact to direct the ball — either fine for a quick single or square for a boundary.",
      "It is an effective shot because it capitalises on the bowler's mistake of pitching too full and straight. Good flickers can manipulate the angle and find gaps with precision.",
      "The flick requires excellent hand-eye coordination and relaxed wrists. Stiff wrists or poor judgement of line can result in a top edge or a nick to short fine leg.",
      "Legends like Zaheer Abbas, Sourav Ganguly, and Yuvraj Singh were considered masters of the flick, regularly piercing the gap at mid-wicket or fine leg for four."
    ],
    tips: ["Let the ball come onto the bat; don't reach for it.", "Relax the wrists — a tense grip kills the timing.", "Pick the gap early: fine leg or mid-wicket.", "Stay side-on; opening up too early results in a mis-hit."]
  },
  "Hook": {
    tag: "Attacking · Leg Side · Cross-Bat",
    facts: [{ label: "Delivery", val: "Short-pitched, at head height" }, { label: "Direction", val: "Fine Leg / Square Leg" }, { label: "Bat swing", val: "Horizontal / Swinging" }, { label: "Risk", val: "Top edge / catch" }],
    youtube: "how to play hook shot cricket short ball head height technique",
    body: [
      "The hook shot is an aggressive cross-bat shot played to a short-pitched delivery that rises to head or shoulder height on the leg side. It is one of the most spectacular shots in cricket when played well.",
      "The batsman rocks back and across, gets inside the line of the ball, and swings the bat in a horizontal arc to send the ball behind square on the leg side, often over the boundary.",
      "The shot demands rapid reflexes, superb footwork to get into position, and the courage to face a ball aimed at the head. It is seen as a badge of honour among batsmen who play it fearlessly.",
      "The risk is significant: a top edge can go straight up for the wicketkeeper or a fielder in the deep. Many batsmen choose to duck or sway out of the way instead of hooking marginal deliveries.",
      "Players like Viv Richards, Gordon Greenidge, and Rohit Sharma have been admired for their decisive, powerful hook shots. The shot can instantly shift momentum in a match."
    ],
    tips: ["Get inside the line — if the ball is straight, let it go.", "Pivot on the back foot to generate the horizontal swing.", "Watch for the fielder at fine leg before committing.", "A helmet with a quality grill is non-negotiable when hooking fast bowling."]
  },
  "Late Cut": {
    tag: "Attacking · Leg Side · Wristy",
    facts: [{ label: "Delivery", val: "Short, wide of off stump" }, { label: "Direction", val: "Behind square (third man)" }, { label: "Touch", val: "Very fine" }, { label: "Foot", val: "Back Foot" }],
    youtube: "how to play late cut cricket shot third man batting tutorial",
    body: [
      "The late cut is one of the most elegant and technically demanding shots in batting. It is played to a short-pitched delivery wide outside off stump, guiding the ball very fine behind point towards the third man boundary.",
      "The striking feature is the 'lateness' of the contact — the batsman waits until the ball is almost past them, then at the last moment angles the bat face and guides the ball at an extreme angle behind square.",
      "This shot requires impeccable timing: too early, and the ball goes to point; too late, and it can hit the bottom edge or even the body. The wrists do the work, not power.",
      "It is most effective against offside bowlers trying to hit a length outside off, as the gap at third man is usually unguarded. In Test cricket, the late cut is used to rotate strike and accumulate singles.",
      "Ricky Ponting, Mark Waugh, and David Gower were renowned for executing delicate late cuts that seemed to defy both physics and the fielding captain's plans."
    ],
    tips: ["Wait, wait, wait — commit to the stroke at the last fraction of a second.", "Stay balanced; don't lunge at the ball.", "Use only the bottom hand for direction; the top hand holds shape.", "Keep the blade angled down to avoid popping up to gully."]
  },
  "Lofted Legside": {
    tag: "Attacking · Leg Side · Aerial",
    facts: [{ label: "Direction", val: "Mid-Wicket / Fine Leg" }, { label: "Foot", val: "Front Foot" }, { label: "Used against", val: "Spin primarily" }, { label: "Intent", val: "Boundary / Six" }],
    youtube: "how to play lofted leg side shot cricket six mid wicket batting",
    body: [
      "The lofted leg-side shot is an aerial attacking stroke played to a delivery on or around the leg stump, hitting the ball over the in-field and into the leg-side boundary area.",
      "It is often used against slow bowlers who pitch on middle and leg: the batsman makes room by adjusting the back foot and swings the bat powerfully through the line, getting the ball airborne over mid-wicket or mid-on.",
      "In limited-overs cricket, this shot is a primary six-scoring mechanism. Power hitters like MS Dhoni, AB de Villiers, and Chris Gayle have developed this into an art form.",
      "The key is to get under the ball and generate enough bat speed to clear the boundary rider. Mis-timing results in a catch at long-on or mid-wicket — a costly error in the final overs of an innings.",
      "Reading the length early is critical. A good-length ball aimed at leg stump is the ideal delivery to loft leg-side, while a full-pitched ball allows more time to generate power."
    ],
    tips: ["Read the length early — this is a pre-meditated shot in T20 cricket.", "Turn the top hand for extra height and loft.", "Aim for the gap between mid-wicket and long-on.", "Follow through fully to maximise bat speed and distance."]
  },
  "Lofted Offside": {
    tag: "Attacking · Off Side · Aerial",
    facts: [{ label: "Direction", val: "Long-off / Long-on" }, { label: "Foot", val: "Front Foot" }, { label: "Shot type", val: "Lofted Drive" }, { label: "Intent", val: "Six / four" }],
    youtube: "how to play lofted off drive cricket aerial six over covers batting",
    body: [
      "The lofted off-side shot is a powerful aerial drive hit over mid-off or extra cover, designed to clear the in-field and reach or clear the boundary on the off side.",
      "It is typically played to a full delivery outside off stump. The batsman drives through the ball with a high follow-through, ensuring the ball climbs over the fielders in the cover region.",
      "This shot is a cornerstone of modern T20 and one-day batting. When executed cleanly, it is one of the most visually impressive strokes in the game — the ball disappearing over the sightscreen at long-off.",
      "The risk is misreading the length and playing a lofted drive to a ball too short, which results in a skier to the fielder. Courage, timing, and a clear sight of the ball are essential.",
      "Kevin Pietersen's Ashes lofted drives and AB de Villiers's off-side aerials are textbook examples of how this shot can change the course of a match single-handedly."
    ],
    tips: ["Get to the pitch of the ball with a big stride before lofting.", "High follow-through — mimic the baseball swing motion.", "Don't tense up: relaxed arms produce cleaner, longer hits.", "Pick your landing zone before the bowler begins their run-up."]
  },
  "Pull": {
    tag: "Attacking · Leg Side · Cross-Bat",
    facts: [{ label: "Delivery", val: "Short, chest/waist height" }, { label: "Direction", val: "Square Leg / Mid-Wicket" }, { label: "Bat swing", val: "Horizontal" }, { label: "Foot", val: "Back Foot" }],
    youtube: "how to play pull shot cricket short ball chest height batting tutorial",
    body: [
      "The pull shot is played to a short-pitched delivery that rises to between chest and waist height. It is a horizontal-bat attacking shot designed to hit the ball through the mid-wicket or square-leg region.",
      "Unlike the hook (which plays to shoulder/head height), the pull is played to a lower ball. The batsman rocks back, swings the bat in a vigorous horizontal arc, and times the ball through the on side.",
      "It is one of the most powerful run-scoring opportunities in cricket and is a staple weapon against any pace attack that over-pitches short. Players use it to punish errant short-pitched bowling.",
      "Footwork is critical: moving back and across to get into line avoids the ball hitting the body and ensures clean contact. Landing on the back foot also creates the space needed for the horizontal swing.",
      "Batsmen like Sachin Tendulkar, Ricky Ponting, and Steve Smith are renowned pull players. The shot requires mental courage — facin a 90mph ball targeting your body and choosing to attack rather than sway."
    ],
    tips: ["Move back and across early — create space between body and ball.", "Roll the wrists at contact to keep the ball on the ground and away from the fielder at square leg.", "Watch the ball's height; anything above shoulder height becomes the hook.", "Keep the elbow high for a clean, flat hitting plane."]
  },
  "Reverse Sweep": {
    tag: "Unconventional · Off Side · Improvised",
    facts: [{ label: "Delivery", val: "Good length, off/middle" }, { label: "Direction", val: "Off Side (reversed)" }, { label: "Innovation", val: "Very High" }, { label: "Risk", val: "High" }],
    youtube: "how to play reverse sweep cricket batting tutorial drills",
    body: [
      "The reverse sweep is one of cricket's most innovative and polarising shots. The batsman reverses their grip on the bat — right-handed batters play left-handed and vice versa — and sweeps the ball to the off side instead of the on side.",
      "It is primarily deployed against spin bowlers to disrupt their field settings. Captains typically set leg-side fields for sweep shots, so reversing the shot direction takes the ball to an unguarded off-side area.",
      "The technique requires exceptional hand-eye coordination, flexibility, and advance planning. The decision to play must be made before the ball is bowled, as there is insufficient time to switch after it is delivered.",
      "The shot has its share of controversy — its inventor Kevin Pietersen and practitioners like Jos Buttler and Eoin Morgan have been criticised for its high dismissal rate, but also praised for its match-changing potential.",
      "When the field is set heavily on the leg side at the death in a T20, the reverse sweep to fine-third becomes a low-risk high-reward option that bowlers cannot easily counter."
    ],
    tips: ["Decide before the bowler bowls — don't improvise at the last second.", "Get the leading knee down for stability and balance.", "Angle the bat face towards third man for best placement.", "Practice switching grip speed until it becomes automatic."]
  },
  "Scoop": {
    tag: "Innovative · Fine Leg · Airborne",
    facts: [{ label: "Delivery", val: "Full, on stumps/body" }, { label: "Direction", val: "Over wicketkeeper / fine leg" }, { label: "Innovation", val: "Extreme" }, { label: "Inventor", val: "Tillakaratne Dilshan" }],
    youtube: "how to play scoop ramp shot cricket over wicketkeeper dilscoop batting",
    body: [
      "The scoop (Dilscoop) is a revolutionary, audacious shot where the batsman squats low or moves to the off side of the ball and scoops it over the wicketkeeper's head, aiming for the fine leg boundary.",
      "Originally invented and popularised by Sri Lankan opener Tillakaratne Dilshan, it exploits the gap behind the wicketkeeper — an area usually devoid of fielders in limited-overs cricket.",
      "The technique involves bending the knees to get below the ball's line, opening the face of the bat at a steep upward angle, and using the bat as a ramp to redirect the ball skyward over the head of the stunned wicketkeeper.",
      "It is most effective against yorker-length or full-pitched deliveries, particularly in the final overs when the bowling attack is trying to hit the feet. The ball's own pace does the work — no power is required.",
      "The danger: if the ball is too short or the timing is off, a top edge goes straight up, offering a simple catch to the keeper or the bowler. Despite the risk, a perfectly executed scoop earns a four or six with almost no effort."
    ],
    tips: ["Get very low — your eyes must be below the ball's path.", "Open the bat face skyward, not forward.", "Move your head outside off stump so the bat goes under the ball.", "Practice the shot against a bowling machine set to full, aimed at middle stump."]
  },
  "Square Cut": {
    tag: "Attacking · Off Side · Back Foot",
    facts: [{ label: "Delivery", val: "Short, wide outside off" }, { label: "Direction", val: "Point / Backward Point" }, { label: "Foot", val: "Back Foot" }, { label: "Bat swing", val: "Horizontal" }],
    youtube: "how to play square cut cricket shot wide outside off stump tutorial",
    body: [
      "The square cut is a powerful, horizontal-bat shot played to a short-pitched delivery well outside the off stump. The ball is hit squarely — perpendicular to the pitch — towards the point or backward point boundary.",
      "The batsman moves back and across, plants the weight firmly on the back foot, and drives the bat across the line in a horizontal arc, hitting the ball with the full face of the bat at shoulder height or lower.",
      "It is among the most satisfying shots in cricket when the timing is perfect. A well-executed square cut splits the gap between gully and point, racing away to the boundary with no chance of interception.",
      "The shot requires judgement: the ball must be short enough and wide enough. Playing a cut to a straight delivery results in either a nick to the keeper or hitting the ball to mid-off via deflection.",
      "Steve Smith, Javed Miandad, and Kevin Pietersen are renowned cut players. The shot is a primary scoring option for openers and top-order batsmen against bowling that strays too wide."
    ],
    tips: ["Get back and across before anything else — rock back decisively.", "The higher the hands at contact, the more control you have.", "Watch for the gully fielder; aim for the gap or along the ground.", "Punch through the ball — don't guide it; hit it away decisively."]
  },
  "Straight Drive": {
    tag: "Attacking · Straight · Textbook",
    facts: [{ label: "Direction", val: "Straight Down the Ground" }, { label: "Foot", val: "Front Foot" }, { label: "Bat swing", val: "Straight" }, { label: "Regarded as", val: "Purest shot in cricket" }],
    youtube: "how to play straight drive cricket batting technique tutorial",
    body: [
      "The straight drive is universally regarded as the most technically pure shot in cricket. It is played to a full-pitched delivery on or very near middle stump, driven back past the bowler along the ground.",
      "The batsman advances the front foot to the pitch of the ball, keeps the head perfectly still with eyes level, and swings the bat in a straight vertical plane — the ideal 'bat coming through straight' that coaches preach.",
      "The shot requires zero deviation of the bat path: any angling of the face sends it towards mid-off or mid-on. When executed perfectly, the ball splits the stumps at the bowler's end and races to the sight screen.",
      "It is often seen as a measure of batting technique — a batsman who executes the straight drive consistently generally has a sound, textbook technique that will succeed at all levels.",
      "Sir Don Bradman, Gordon Greenidge, and Virat Kohli have been particularly celebrated for their straight drives, which are often described as 'bisecting the ground' due to their precision."
    ],
    tips: ["Lead with the head — get it over the front knee and directly above the ball.", "The bat should follow the line of your leading shoulder, which should be pointing straight at the bowler.", "Soft top hand, firm bottom hand at impact.", "Transfer weight smoothly from back to front foot as the ball arrives."]
  },
  "Sweep": {
    tag: "Attacking · Leg Side · Against Spin",
    facts: [{ label: "Delivery", val: "Good length, on leg stump" }, { label: "Direction", val: "Fine Leg / Backward Square" }, { label: "Used against", val: "Spin bowling" }, { label: "Foot", val: "Front Foot" }],
    youtube: "how to play sweep shot cricket against spin bowling tutorial drills",
    body: [
      "The sweep is a front-foot cross-bat shot played specifically against spin bowling to a delivery pitching on middle or leg stump at a good length. The ball is swept around the corner towards the fine leg or backward square leg area.",
      "The batsman advances the front foot, bends both knees to get low, and sweeps the bat in a horizontal arc from right to left (for a right-hander), making contact with the ball at a very low height near the ground.",
      "It is one of the most important attacking options against spin because it disrupts the spinner's line and length, targeting the unguarded leg-side region where fielders are rarely stationed.",
      "The shot has a low margin for error: an LBW decision is possible if the front pad is in line, and a top edge can go straight to short fine leg. Players must assess the ball's pitch and trajectory accurately.",
      "England have been particularly adept sweepers throughout history — players like Graeme Swann (as a tailender batsman) and Joe Root use it as a primary scoring shot against left-arm spin and off-spin."
    ],
    tips: ["Get your front knee down close to the pitch of the ball.", "Make contact in front of the pad — not beside or behind it — to avoid LBW.", "Adjust the angle of the bat face to direct between square leg and fine leg.", "Disguise the shot as long as possible to prevent the bowler adjusting."]
  },
  "Upper Cut": {
    tag: "Audacious · Off Side · Aerial",
    facts: [{ label: "Delivery", val: "Short, wide, above shoulder height" }, { label: "Direction", val: "Third Man / Fine Third" }, { label: "Risk", val: "High" }, { label: "Effect", val: "Boundary / Six over third man" }],
    youtube: "how to play upper cut cricket short wide ball third man boundary tutorial",
    body: [
      "The upper cut is a bold, improvised shot played to a short-pitched delivery that rises steeply and is wide outside off stump, slapping the ball with an upward bat angle towards third man — often for four or six.",
      "It requires the batsman to stand tall, get behind the line of the ball, and make a punching or swatting motion with the bat angled upwards, guiding the ball over the fielder at third man.",
      "The shot was popularised in the early 2000s T20 era when batsmen were looking for ways to score off short-pitched, wide deliveries that were previously considered 'safe' by bowlers.",
      "The upper cut is difficult to defend against because a short ball outside off stump has traditionally been non-threatening — but the upper cut turns it into a boundary opportunity. It also unsettles bowlers psychologically.",
      "The biggest risk is a thick edge or mis-direction: if the ball is not as wide as anticipated, the edge can go to third slip or gully. Players like Adam Gilchrist, Virender Sehwag, and Brendon McCullum used it ruthlessly."
    ],
    tips: ["Identify width early — this only works if the ball is genuinely wide outside off.", "Don't reach for the ball; let it come to you and time the upward bat movement.", "Aim over third man where deep fielders are rarely placed.", "Practice off a high-feed bowling machine to get used to the height."]
  },
  "drive": {
    tag: "Classical · Both Sides · Front Foot",
    facts: [{ label: "Foot", val: "Front Foot" }, { label: "Delivery", val: "Full length, on or off stump" }, { label: "Direction", val: "Off / On / Straight" }, { label: "Regarded as", val: "Cornerstone of batting" }],
    youtube: "how to play drive shot cricket off drive on drive front foot batting tutorial",
    body: [
      "The drive is the cornerstone of classical batting technique. Played off the front foot to a full-pitched or half-volley delivery, it is a straight-bat stroke designed to hit the ball along the ground through various gaps in the field.",
      "The on drive sends the ball through mid-on, the off drive through extra cover or mid-off, and the straight drive directly back past the bowler. The footwork, head position, and bat swing are essentially identical — only the angle of the shoulders and the direction of the front foot changes.",
      "A perfect drive requires the batsman to get fully to the pitch of the ball: head forward, front knee bent, eyes level. This ensures the ball is met at its highest point, giving the batsman maximum control over the angle.",
      "The drive is the most versatile scoring shot in Test cricket and forms the basis of a batsman's off-side and on-side game. Young batsmen are taught the drive before any other attacking shot.",
      "Don Bradman, Graeme Pollock, and Kumar Sangakkara are regarded as among the finest drivers in cricket history, with drives that were both powerful and aesthetically beautiful."
    ],
    tips: ["Never drive without getting to the pitch — if in doubt, don't drive.", "Head over the ball, not tilted back, to keep it on the ground.", "Point the front shoulder towards the intended direction of the drive.", "Avoid the 'tennis forehand' error: keep the bat face straight through contact."]
  },
  "legglance-flick": {
    tag: "Touch Shot · Leg Side · Off the Hip",
    facts: [{ label: "Delivery", val: "Full, on leg / body" }, { label: "Direction", val: "Fine Leg / Backward Square" }, { label: "Power", val: "Minimal" }, { label: "Key skill", val: "Wrist and timing" }],
    youtube: "how to play leg glance flick shot cricket wrist leg side tutorial",
    body: [
      "The leg glance and flick is a combination of two closely related shots: the glance angles the ball very fine with a minimal bat movement, while the flick uses a more active wrist to deflect the ball squarer.",
      "Both shots are played to deliveries aimed at the leg stump or into the body. Instead of defending or trying to hit across the line, the batsman uses soft hands and wrist rotation to redirect the ball off the bat.",
      "The leg glance is considered one of the most classical strokes in batting — old-school Test batsmen would consistently pick up easy runs behind square leg with a subtle turn of the wrists.",
      "The flick version of the shot involves a more committed wrist action, sending the ball at a wider angle — towards square leg rather than fine leg. This version brings greater scoring opportunities but also greater risk of a miscue.",
      "Both require the batsman to assess whether to play with or against the ball: trying to force the ball leg side when it is aimed at the pad often leads to an uncontrolled hit. The timing of the wrist action is everything."
    ],
    tips: ["Open the face only at the moment of contact — not before.", "Let the ball come to you; reaching across the line is dangerous.", "Keep the head still; dropping the head leads to a mis-timed top edge.", "A light grip improves wrist flexibility and timing dramatically."]
  },
  "pullshot": {
    tag: "Attacking · Leg Side · Power",
    facts: [{ label: "Delivery", val: "Short, at chest/waist height" }, { label: "Direction", val: "Mid-Wicket / Square Leg" }, { label: "Foot", val: "Back Foot" }, { label: "Power", val: "High" }],
    youtube: "how to play pull shot cricket mid wicket back foot short ball power batting",
    body: [
      "The pull shot is a high-power back-foot stroke played to a short-pitched delivery rising to chest or waist height. It is struck with a horizontal bat across the line of the ball, sending it to the mid-wicket or square leg region.",
      "It is one of the most satisfying shots in batting when executed cleanly — the combination of pace off the bat and the natural speed of the delivery makes the ball race to the boundary in an instant.",
      "Executing the pull requires getting back and across quickly, planting the back foot firmly, and generating bat speed through a full horizontal arc. The earlier the weight transfer, the more authoritative the shot.",
      "The shot is a defensive weapon as well: by pulling short balls confidently, the batsman signals to the bowler that the short-pitch attack will not work, forcing a change in strategy.",
      "Batsmen who lack the pull shot are targeted heavily by fast bowlers. Conversely, those who pull well — like Andrew Symonds, Rohit Sharma, and David Warner — tend to score at higher strike rates and dominate pace attacks that stray short."
    ],
    tips: ["Move back and across before the ball pitches — early feet save everything.", "Roll the wrists through the shot to smother the top edge risk.", "Aim to hit the ball to mid-wicket on the ground, not over it — six is a bonus.", "Practice the shot off a short-pitch bowling machine to improve reflexes."]
  }
};

const ALL_SHOTS = Object.keys(SHOT_META);

// ─── State ─────────────────────────────────────────────────────────
let currentMode = "image";   // "image" | "video"
let selectedFile = null;
let isLoading = false;

// ─── DOM Refs ───────────────────────────────────────────────────────
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const btnBrowse = document.getElementById("btn-browse");
const btnPredict = document.getElementById("btn-predict");
const btnClear = document.getElementById("btn-clear");
const btnSpinner = document.getElementById("btn-spinner");
const btnText = document.querySelector(".btn-text");
const previewContainer = document.getElementById("preview-container");
const previewImage = document.getElementById("preview-image");
const previewVideo = document.getElementById("preview-video");
const previewLabel = document.getElementById("preview-label");
const fileMeta = document.getElementById("file-meta");
const dropText = document.getElementById("drop-text");
const dropHint = document.getElementById("drop-hint");
const btnImage = document.getElementById("btn-image");
const btnVideo = document.getElementById("btn-video");
const securityPill = document.getElementById("security-pill");  // may be null — safe to use with ?.
const performanceSection = document.getElementById("performance-section");  // may be null
const heatmapImage = document.getElementById("heatmap-image");  // may be null
const confusionInsightsList = document.getElementById("confusion-insights-list");  // may be null

// ─── Result card state refs ─────────────────────────────────────────
const emptyState = document.getElementById("empty-state");
const loadingState = document.getElementById("loading-state");
const resultContent = document.getElementById("result-content");
const errorState = document.getElementById("error-state-result");
const errorMsg = document.getElementById("error-msg-result");
const btnRetry = document.getElementById("btn-retry-result");

const confBadge = document.getElementById("conf-badge-result");
const confValue = document.getElementById("conf-value-result");
const confFill = document.getElementById("conf-fill-result");
const shotDescription = document.getElementById("shot-description-result");
const annotatedImage = document.getElementById("annotated-image-result");
const noSkeleton = document.getElementById("no-skeleton-result");
const top5List = document.getElementById("top5-list-result");
const videoMeta = document.getElementById("video-meta-result");
const frameCountPill = document.getElementById("frame-count-pill-result");
const framesProcessPill = document.getElementById("frames-processed-pill-result");

// ─── Auth DOM Refs ──────────────────────────────────────────────────
const authModal = document.getElementById("auth-modal-overlay");
const btnShowAuth = document.getElementById("btn-show-auth");
const btnLogout = document.getElementById("btn-logout");
const userProfile = document.getElementById("user-profile");
const userDisplayName = document.getElementById("user-display-name");

const authViews = document.querySelectorAll(".auth-content");
const authTabs = document.querySelectorAll(".auth-tab");
const authError = document.getElementById("auth-error");
const authErrorText = authError ? authError.querySelector('.error-text') : null;

const formLogin  = document.getElementById("form-login");
const formSignup = document.getElementById("form-signup");
const formOtp    = document.getElementById("form-otp");
const formForgot = document.getElementById("form-forgot");
const formReset  = document.getElementById("form-reset");

const groupEmail = document.getElementById("group-email");
const groupPassword = document.getElementById("group-password");
const groupMobile = document.getElementById("group-mobile");

const otpInputs = document.querySelectorAll(".otp-field");
const otpTargetLabel = document.getElementById("otp-target-label");

let currentAuthUser = null;
let authState = { userId: null, method: 'email', flow: 'login' };


// ─── Particle Canvas ────────────────────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById("particles-canvas");
  const ctx = canvas.getContext("2d");
  let particles = [];
  const N = 80;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function random(min, max) { return Math.random() * (max - min) + min; }

  function createParticle() {
    return {
      x: random(0, canvas.width),
      y: random(0, canvas.height),
      r: random(0.8, 2.5),
      dx: random(-0.25, 0.25),
      dy: random(-0.3, -0.05),
      alpha: random(0.2, 0.7)
    };
  }

  function init() { particles = Array.from({ length: N }, createParticle); }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 232, 138, ${p.alpha})`;
      ctx.fill();

      p.x += p.dx;
      p.y += p.dy;
      p.alpha -= 0.0008;

      if (p.alpha <= 0 || p.y < -10) {
        Object.assign(p, createParticle(), { y: canvas.height + 5, alpha: random(0.2, 0.6) });
      }
    });
    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", () => { resize(); init(); });
  resize();
  init();
  draw();
})();

// ─── Shot Cards Reference Grid ──────────────────────────────────────
function buildShotsGrid() {
  const grid = document.getElementById("shots-grid");
  ALL_SHOTS.forEach((shot, idx) => {
    const meta = SHOT_META[shot];
    const card = document.createElement("div");
    card.className = "shot-card";
    card.style.animationDelay = `${idx * 40}ms`;
    card.setAttribute("aria-label", `Learn about ${shot}`);
    card.innerHTML = `
      <span class="shot-card-icon">${meta.emoji}</span>
      <div class="shot-card-name">${shot}</div>
    `;
    card.addEventListener("click", () => openShotModal(shot));
    grid.appendChild(card);
  });
}

buildShotsGrid();

// ─── Shot Detail Modal ───────────────────────────────────────────────
const modalOverlay = document.getElementById("modal-overlay");
const modalClose = document.getElementById("modal-close");
const modalEmoji = document.getElementById("modal-emoji");
const modalTag = document.getElementById("modal-tag");
const modalTitle = document.getElementById("modal-title");
const modalFacts = document.getElementById("modal-facts");
const modalBody = document.getElementById("modal-body");
const modalTips = document.getElementById("modal-tips");

function openShotModal(shot) {
  const meta = SHOT_META[shot] || { emoji: "🏏" };
  const detail = SHOT_DETAIL[shot] || { tag: "", facts: [], body: ["No description available."], tips: [] };

  // Populate header
  modalEmoji.textContent = meta.emoji;
  modalTag.textContent = detail.tag || "Cricket Shot";
  modalTitle.textContent = shot;

  // Facts chips
  modalFacts.innerHTML = detail.facts.map(f =>
    `<div class="fact-chip">${f.label} <span>${f.val}</span></div>`
  ).join("");

  // Body paragraphs
  modalBody.innerHTML = detail.body.map(p => `<p>${p}</p>`).join("");

  // Tips
  modalTips.innerHTML = detail.tips.map(t => `<li>${t}</li>`).join("");

  // YouTube link — uses a search query for guaranteed relevance
  const existingYt = document.getElementById("modal-yt-link");
  if (existingYt) existingYt.remove();
  if (detail.youtube) {
    const searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(detail.youtube)}`;
    const ytLink = document.createElement("a");
    ytLink.id = "modal-yt-link";
    ytLink.href = searchUrl;
    ytLink.target = "_blank";
    ytLink.rel = "noopener noreferrer";
    ytLink.className = "yt-watch-btn";
    ytLink.innerHTML = `
      <svg class="yt-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" fill="#FF0000"/>
      </svg>
      <span>Watch on YouTube</span>
    `;
    document.getElementById("modal-tips-wrap").after(ytLink);
  }

  // Open modal
  document.body.style.overflow = "hidden";
  modalOverlay.classList.add("open");
  modalClose.focus();
}

function closeShotModal() {
  modalOverlay.classList.remove("open");
  document.body.style.overflow = "";
}

// Close on button, overlay click, or Escape key
modalClose.addEventListener("click", closeShotModal);
modalOverlay.addEventListener("click", e => { if (e.target === modalOverlay) closeShotModal(); });

// ─── Analysis Result State Management ────────────────────────────────
function showEmptyState() {
  emptyState.style.display = "flex";
  loadingState.style.display = "none";
  resultContent.style.display = "none";
  document.getElementById("error-state-result").style.display = "none";
}
function showLoadingState() {
  emptyState.style.display = "none";
  loadingState.style.display = "flex";
  resultContent.style.display = "none";
  document.getElementById("error-state-result").style.display = "none";
}
function showResultContent() {
  emptyState.style.display = "none";
  loadingState.style.display = "none";
  resultContent.style.display = "block";
  document.getElementById("error-state-result").style.display = "none";
}

// ─── Modal shims (for analysis modals removed from new HTML) ──────
function openAnalysisModal() { } // now inline in result card
function closeAnalysisModal() { }

document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    if (modalOverlay.classList.contains("open")) closeShotModal();
    if (authModal && authModal.classList.contains("open")) authModal.classList.remove("open");
  }
});

// ─── Mode Toggle ────────────────────────────────────────────────────
function setMode(mode) {
  currentMode = mode;
  btnImage.classList.toggle("active", mode === "image");
  btnVideo.classList.toggle("active", mode === "video");

  if (mode === "image") {
    fileInput.accept = "image/jpeg,image/png,image/webp,image/*";
    dropText.innerHTML = `Drop your <strong>cricket image</strong> here`;
    dropHint.textContent = "JPG · PNG · WEBP supported";
  } else {
    fileInput.accept = "video/mp4,video/quicktime,video/x-msvideo,video/*";
    dropText.innerHTML = `Drop your <strong>cricket video</strong> here`;
    dropHint.textContent = "MP4 · AVI · MOV · MKV supported";
  }

  clearFile();
}

btnImage.addEventListener("click", () => setMode("image"));
btnVideo.addEventListener("click", () => setMode("video"));

// ─── File Handling ──────────────────────────────────────────────────
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function showPreview(file) {
  selectedFile = file;
  const url = URL.createObjectURL(file);

  if (currentMode === "image") {
    previewImage.src = url;
    previewImage.style.display = "block";
    previewVideo.style.display = "none";
  } else {
    previewVideo.src = url;
    previewVideo.style.display = "block";
    previewImage.style.display = "none";
  }

  previewLabel.textContent = file.name;
  fileMeta.textContent = `${formatSize(file.size)} · ${file.type || "unknown"}`;
  previewContainer.style.display = "block";
  dropZone.style.display = "none";
  btnPredict.disabled = false;
}

function clearFile() {
  selectedFile = null;
  previewImage.src = "";
  previewVideo.src = "";
  previewImage.style.display = "none";
  previewVideo.style.display = "none";
  previewContainer.style.display = "none";
  dropZone.style.display = "block";
  btnPredict.disabled = true;
}

btnClear.addEventListener("click", clearFile);
btnRetry.addEventListener("click", clearFile);

btnBrowse.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", e => {
  const file = e.target.files[0];
  if (file) { showPreview(file); fileInput.value = ""; }
});

// ─── Drag & Drop ────────────────────────────────────────────────────
dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));

dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) showPreview(file);
});

dropZone.addEventListener("click", e => {
  if (e.target !== btnBrowse) fileInput.click();
});

// ─── UI State Functions ─────────────────────────────────────────────
function showLoading() {
  isLoading = true;
  btnText.textContent = "Analysing…";
  btnSpinner.style.display = "inline-block";
  btnPredict.disabled = true;
  showLoadingState();
}

function hideLoading() {
  isLoading = false;
  btnText.textContent = "🎯 Analyse Shot";
  btnSpinner.style.display = "none";
  btnPredict.disabled = false;
}

function showError(msg) {
  emptyState.style.display = "none";
  loadingState.style.display = "none";
  resultContent.style.display = "none";
  errorState.style.display = "flex";
  errorMsg.textContent = msg;
}

// ─── Render Results ─────────────────────────────────────────────────
function renderResult(data, isVideo) {
  showResultContent();
  // Scroll to result card on mobile
  document.getElementById("result-card")?.scrollIntoView({ behavior: "smooth", block: "start" });

  const meta = SHOT_META[data.shot] || { emoji: "🏏", desc: "" };
  const confPct = Math.round(data.confidence * 100);

  // Shot banner
  document.getElementById("shot-emoji-result").textContent = meta.emoji;
  document.getElementById("shot-name-result").textContent = data.shot;
  document.getElementById("conf-badge-result").textContent = `${confPct}%`;

  // Confidence bar (animate after paint)
  document.getElementById("conf-value-result").textContent = `${confPct}%`;
  const confFill = document.getElementById("conf-fill-result");
  confFill.style.width = "0%";
  setTimeout(() => { confFill.style.width = `${confPct}%`; }, 80);

  // Description
  document.getElementById("shot-description-result").textContent = meta.desc || "No description available.";

  // Annotated media
  const annotatedImage = document.getElementById("annotated-image-result");
  const noSkeleton = document.getElementById("no-skeleton-result");

  annotatedImage.style.display = "none";
  noSkeleton.style.display = "none";

  if (data.annotated_image) {
    annotatedImage.src = data.annotated_image;
    annotatedImage.style.display = "block";
  } else {
    noSkeleton.style.display = "block";
  }

  // Top-5
  const top5List = document.getElementById("top5-list-result");
  top5List.innerHTML = "";
  if (data.all_scores) {
    data.all_scores.forEach((item, idx) => {
      const pct = Math.round(item.confidence * 100);
      const row = document.createElement("div");
      row.className = "top5-item";
      row.style.animationDelay = `${idx * 80}ms`;
      row.innerHTML = `
        <span class="top5-rank">#${idx + 1}</span>
        <div class="top5-bar-wrap">
          <div class="top5-bar rank-${idx + 1}" style="width:0%" data-width="${pct}%"></div>
        </div>
        <span class="top5-name">${item.shot}</span>
        <span class="top5-pct">${pct}%</span>
      `;
      top5List.appendChild(row);
      // animate bars
      setTimeout(() => {
        row.querySelector(".top5-bar").style.width = `${pct}%`;
      }, 120 + idx * 80);
    });
  }

  // Video meta
  const videoMeta = document.getElementById("video-meta-result");
  const frameCountPill = document.getElementById("frame-count-pill-result");
  const framesProcessPill = document.getElementById("frames-processed-pill-result");

  if (isVideo) {
    videoMeta.style.display = "flex";
    frameCountPill.textContent = `${data.frame_count ?? "?"} total frames`;
    framesProcessPill.textContent = `${data.frames_processed ?? "?"} analysed`;
  } else {
    videoMeta.style.display = "none";
  }
}

// ─── Predict Action ─────────────────────────────────────────────────
btnPredict.addEventListener("click", async () => {
  if (!selectedFile || isLoading) return;

  // Check 3 free predictions logic if not logged in
  if (!currentAuthUser) {
    let freePredictions = parseInt(localStorage.getItem("free_predictions") || "0", 10);
    if (freePredictions >= 3) {
      showAuthView("login");
      authModal.classList.add("open");
      showAuthError("You've used all 3 free predictions. Please sign in to continue.");
      return;
    }
  }

  showLoading();

  const endpoint = currentMode === "image"
    ? `${API_BASE}/predict/image`
    : `${API_BASE}/predict/video`;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
      credentials: 'include'
    });

    // Check if response is JSON before parsing (cold-start Render returns HTML 502)
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      // Server returned HTML (e.g. 502 gateway page from Render cold start)
      showError("Server is starting up — please wait 30 seconds and try again.");
      hideLoading();
      return;
    }

    let data;
    try {
      data = await response.json();
    } catch (jsonErr) {
      showError("Server is starting up — please wait 30 seconds and try again.");
      hideLoading();
      return;
    }

    if (!response.ok) {
      // Handle free limit reached
      if (data.error === "free_limit_reached") {
        showError("You've used all 3 free predictions. Please sign in to continue.");
        showAuthView("login");
        authModal.classList.add("open");
      } else {
        showError(data.error || `Server error (${response.status}).`);
      }
    } else if (data.error && !data.annotated_image && !data.shot) {
      // Pure error with no usable result
      showError(data.error);
    } else {
      renderResult(data, currentMode === "video");

      // If there was a partial error (no skeleton detected) show message in result
      if (data.error && !data.annotated_image) {
        document.getElementById("no-skeleton-result").style.display = "block";
        document.getElementById("annotated-image-result").style.display = "none";
      }

      // Increment free predictions counter (client-side fallback)
      if (!currentAuthUser) {
        let freePredictions = parseInt(localStorage.getItem("free_predictions") || "0", 10);
        localStorage.setItem("free_predictions", freePredictions + 1);
      }
    }
  } catch (err) {
    if (err.name === "TypeError" || err.message?.includes("fetch")) {
      showError("Cannot connect to server. Make sure the Flask server is running on port 5000.");
    } else {
      showError(`Unexpected error: ${err.message}`);
    }
  } finally {
    hideLoading();
  }
});

// ─── Initial State ──────────────────────────────────────────────────────────
showEmptyState();
checkAuthStatus();
loadStats();
// loadMetrics(); // Function not defined, causes ReferenceError

// ─── Server Warm-up Check (for Render cold starts) ──────────────────────────
(function checkServerReady() {
  const banner = document.createElement("div");
  banner.id = "server-warming-banner";
  banner.style.cssText = `
    position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
    background:#1a2a3a;border:1px solid #00e88a;color:#00e88a;
    padding:12px 24px;border-radius:8px;font-size:14px;z-index:9999;
    display:none;text-align:center;box-shadow:0 4px 20px rgba(0,232,138,0.2);
  `;
  banner.innerHTML = "⏳ Server is waking up (free tier cold start)... please wait";
  document.body.appendChild(banner);

  let attempts = 0;
  const maxAttempts = 20; // 60 seconds total

  function ping() {
    fetch("/health")
      .then(r => r.json())
      .then(d => {
        if (d.status === "ok") {
          banner.style.display = "none";
        } else {
          retry();
        }
      })
      .catch(() => retry());
  }

  function retry() {
    attempts++;
    if (attempts >= maxAttempts) {
      banner.innerHTML = "⚠️ Server may be down. Please refresh the page.";
      banner.style.borderColor = "#ff4444";
      banner.style.color = "#ff4444";
      banner.style.display = "flex";
      return;
    }
    banner.style.display = "flex";
    setTimeout(ping, 3000);
  }

  // Start polling after 2 seconds (give server a chance to be ready)
  setTimeout(ping, 2000);
})();


// ─── Load Stats from /stats endpoint ───────────────────────────────────
function loadStats() {
  fetch(`${API_BASE}/stats`, { credentials: 'include' })
    .then(r => r.json())
    .then(d => {
      const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
      el("stat-total-preds", d.total_predictions ?? 0);
      el("stat-users", d.registered_users ?? 0);
      el("stat-top-shot", d.top_shots?.[0]?.shot ?? "N/A");
    })
    .catch(() => { }); // silently ignore if server not ready yet
}

// ─── Authentication Logic ───────────────────────────────────────────
function checkAuthStatus() {
  fetch(`${API_BASE}/auth/status`, { credentials: 'include' })
    .then(r => r.json())
    .then(data => {
      if (data.is_logged_in) {
        updateAuthUI(data.user);
      } else {
        updateAuthUI(null);
      }
    })
    .catch(() => {
      // Server not reachable — show logged-out state silently
      updateAuthUI(null);
    });
}

function updateAuthUI(user) {
  currentAuthUser = user;
  const freeEl = document.getElementById("free-counter");
  if (user) {
    if (btnShowAuth) btnShowAuth.style.display = "none";
    if (userProfile) userProfile.style.display = "flex";
    if (userDisplayName) userDisplayName.textContent = user.email || user.mobile || "User";
    const avatar = document.getElementById("user-avatar");
    if (avatar) avatar.textContent = (user.email || user.mobile || "U")[0].toUpperCase();
    if (freeEl) freeEl.style.display = "none";
    if (securityPill) securityPill.style.display = "flex";
  } else {
    if (btnShowAuth) btnShowAuth.style.display = "block";
    if (userProfile) userProfile.style.display = "none";
    const used = parseInt(localStorage.getItem("free_predictions") || "0", 10);
    const remaining = Math.max(0, 3 - used);
    if (freeEl) {
      freeEl.textContent = `${remaining} free left`;
      freeEl.style.display = remaining > 0 ? "block" : "none";
    }
    if (securityPill) securityPill.style.display = "none";
  }
}


// Modal Management
btnShowAuth.addEventListener("click", () => {
  showAuthView("login");
  authModal.classList.add("open");
});

document.getElementById("auth-modal-close").addEventListener("click", () => {
  authModal.classList.remove("open");
});

function showAuthView(viewId) {
  authViews.forEach(v => v.classList.remove("active"));
  document.getElementById(`auth-view-${viewId}`).classList.add("active");
  authError.style.display = "none";
}

// Login toggles
document.getElementById("link-back-to-login").addEventListener("click", e => { e.preventDefault(); authState.flow = 'login'; showAuthView("login"); });
document.getElementById("link-forgot-password").addEventListener("click", e => { e.preventDefault(); showAuthView("forgot"); });
document.getElementById("link-to-signup").addEventListener("click", e => { e.preventDefault(); authState.flow = 'login'; showAuthView("signup"); });
document.getElementById("link-to-login").addEventListener("click", e => { e.preventDefault(); authState.flow = 'login'; showAuthView("login"); });

// Email/Mobile Tabs Removed

// Form Submissions
formLogin.addEventListener("submit", async e => {
  e.preventDefault();
  const payload = {
    email: document.getElementById("login-email").value,
    password: document.getElementById("login-password").value
  };

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: 'include'
  });
  const data = await res.json();
  if (res.ok) {
    if (data.type === "otp_required") {
      authState.userId = data.user_id;
      otpTargetLabel.textContent = `Enter the 6-digit OTP sent to ${payload.email}`;
      showAuthView("otp");
      if (data.otp_debug) showOtpToast(data.otp_debug);
    }
  } else {
    showAuthError(data.error);
  }
});

formSignup.addEventListener("submit", async e => {
  e.preventDefault();
  const payload = {
    email: document.getElementById("signup-email").value,
    password: document.getElementById("signup-password").value
  };

  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: 'include'
  });
  const data = await res.json();
  if (res.ok) {
    authState.userId = data.user_id;
    otpTargetLabel.textContent = `Enter the 6-digit OTP sent to ${payload.email}`;
    showAuthView("otp");
    if (data.otp_debug) showOtpToast(data.otp_debug);
  } else {
    showAuthError(data.error);
  }
});



formOtp.addEventListener("submit", async e => {
  e.preventDefault();
  const otp = Array.from(otpInputs).map(i => i.value).join("");

  if (otp.length < 6) {
    showAuthError("Please enter all 6 digits of the OTP.");
    return;
  }

  if (authState.flow === 'reset') {
    // Store OTP and show the set-new-password view.
    // The backend will validate the OTP when /auth/reset-password is called.
    authState.resetOtp = otp;
    otpInputs.forEach(i => i.value = "");
    showAuthView("reset");
    return;
  }

  // Normal login/signup flow
  const res = await fetch(`${API_BASE}/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: authState.userId, otp }),
    credentials: 'include'
  });
  const data = await res.json();
  if (res.ok) {
    authModal.classList.remove("open");
    checkAuthStatus();
    showSuccessToast("Login Successful! Enjoy CRICSHOT! 🏏");
  } else {
    showAuthError("Invalid or expired OTP. Please try again.");
  }
});

// ─── Resend OTP handler ─────────────────────────────────────────────
const btnResendOtp = document.getElementById("btn-resend-otp");
if (btnResendOtp) {
  btnResendOtp.addEventListener("click", async () => {
    if (!authState.userId) {
      showAuthError("Session expired. Please start login again.");
      showAuthView("login");
      return;
    }
    btnResendOtp.disabled = true;
    btnResendOtp.textContent = "Sending...";
    try {
      const res = await fetch(`${API_BASE}/auth/resend-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: authState.userId }),
        credentials: 'include'
      });
      const data = await res.json();
      if (res.ok) {
        btnResendOtp.textContent = "Resent!";
        if (data.otp_debug) showOtpToast(data.otp_debug);
        setTimeout(() => { btnResendOtp.textContent = "Resend code"; btnResendOtp.disabled = false; }, 30000);
      } else {
        showAuthError(data.error || "Failed to resend OTP.");
        btnResendOtp.textContent = "Resend code";
        btnResendOtp.disabled = false;
      }
    } catch {
      showAuthError("Could not connect to server.");
      btnResendOtp.textContent = "Resend code";
      btnResendOtp.disabled = false;
    }
  });
}

formForgot.addEventListener("submit", async e => {
  e.preventDefault();
  const payload = { email: document.getElementById("forgot-target").value };

  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: 'include'
  });
  const data = await res.json();
  if (res.ok) {
    authState.userId = data.user_id;
    authState.flow   = 'reset';   // mark as reset flow
    otpTargetLabel.textContent = `Enter the OTP sent to ${payload.email} to reset your password`;
    showAuthView("otp");
    if (data.otp_debug) showOtpToast(data.otp_debug);
  } else {
    showAuthError(data.error);
  }
});

// Reset password form — called after OTP verified in reset flow
formReset.addEventListener("submit", async e => {
  e.preventDefault();
  const newPass     = document.getElementById("reset-new-password").value;
  const confirmPass = document.getElementById("reset-confirm-password").value;

  if (newPass !== confirmPass) {
    showAuthError("Passwords do not match. Please try again.");
    return;
  }
  if (newPass.length < 6) {
    showAuthError("Password must be at least 6 characters.");
    return;
  }

  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: authState.userId, otp: authState.resetOtp, password: newPass }),
    credentials: 'include'
  });
  const data = await res.json();
  if (res.ok) {
    // Clear fields
    document.getElementById("reset-new-password").value = "";
    document.getElementById("reset-confirm-password").value = "";
    authState.flow = 'login';
    authState.resetOtp = null;
    showAuthView("login");
    // Show success message briefly
    showAuthError("Password reset successfully! Please sign in.");
    setTimeout(() => { authError.style.display = "none"; }, 3000);
  } else {
    showAuthError(data.error || "Reset failed. Please request a new OTP.");
  }
});

document.getElementById("link-reset-back-login").addEventListener("click", e => {
  e.preventDefault();
  authState.flow = 'login';
  authState.resetOtp = null;
  showAuthView("login");
});

btnLogout.addEventListener("click", async () => {
  try {
    await fetch(`${API_BASE}/auth/logout`, { credentials: 'include' });
  } catch (e) { /* ignore network errors */ }
  currentAuthUser = null;
  localStorage.removeItem("free_predictions");
  updateAuthUI(null);
  clearFile();
});

function showAuthError(msg) {
  if (authErrorText) {
    authErrorText.textContent = msg;
    authError.style.display = "flex";
  } else {
    authError.textContent = msg;
    authError.style.display = "block";
  }
}

// OTP Input behavior
otpInputs.forEach((input, idx) => {
  input.addEventListener("input", e => {
    if (e.target.value && idx < otpInputs.length - 1) {
      otpInputs[idx + 1].focus();
    }
  });
  input.addEventListener("keydown", e => {
    if (e.key === "Backspace" && !e.target.value && idx > 0) {
      otpInputs[idx - 1].focus();
    }
  });
});

// ─── Development Helpers ────────────────────────────────────────────
function showOtpToast(otp) {
  // Remove existing toasts first
  const existing = document.querySelectorAll(".otp-toast");
  existing.forEach(t => t.remove());

  const toast = document.createElement("div");
  toast.className = "otp-toast";
  toast.innerHTML = `
    <div class="otp-toast-title">Instant OTP (Development)</div>
    <div class="otp-toast-code">${otp}</div>
    <div class="otp-toast-hint">Sent via email if configured. Click to dismiss.</div>
  `;

  toast.addEventListener("click", () => toast.remove());
  document.body.appendChild(toast);

  // Auto-remove after 30 seconds
  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 30000);
}

// ─── Success Toast ───────────────────────────────────────────────────
function showSuccessToast(msg) {
  const existing = document.querySelectorAll(".success-toast");
  existing.forEach(t => t.remove());

  const toast = document.createElement("div");
  toast.className = "success-toast";
  toast.style.cssText = `
    position:fixed;bottom:20px;right:20px;
    background:linear-gradient(135deg,#00e88a,#00c070);
    color:#0d1b2a;padding:14px 22px;border-radius:10px;
    font-size:14px;font-weight:600;z-index:99999;
    box-shadow:0 4px 20px rgba(0,232,138,0.35);
    animation:slideInRight 0.3s ease;
  `;
  toast.textContent = msg;
  toast.addEventListener("click", () => toast.remove());
  document.body.appendChild(toast);
  setTimeout(() => { if (toast.parentElement) toast.remove(); }, 4000);
}
