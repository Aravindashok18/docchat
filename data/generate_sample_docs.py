"""Generate the two synthetic PDFs the demo and the eval set are built on.

Both documents are made up (a fictional espresso machine manual and a
fictional savings-account agreement). Every page carries a running header and
a "Page N" footer, like a real document would, so the cleaning step has
something to strip out.

    python data/generate_sample_docs.py
"""
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT_DIR = Path(__file__).resolve().parent / "docs"

AURORA_PAGES = [
    (
        "Safety and Setup",
        [
            "Read all instructions before using the Aurora X200. Keep the machine out of reach of "
            "children under eight years of age. Place the machine on a flat, heat-resistant surface "
            "and leave at least 15 cm of free space above and 10 cm on each side so that steam can "
            "escape safely. Never operate the machine without water in the tank, and never immerse "
            "the base, power cord or plug in water.",
            "The Aurora X200 runs on 230 V at 50 Hz and draws 1450 W when the boiler is heating. The "
            "power cord is 1.2 m long. Do not use an extension cord. If the supply cord is damaged, "
            "it must be replaced by the manufacturer or its service agent.",
            "The removable water tank holds 1.8 litres when filled to the MAX line. Use fresh, cold "
            "drinking water only. Do not fill the tank with milk, coffee or any other liquid. Empty "
            "and refill the tank every day for the best flavour; water that has been sitting for "
            "more than 24 hours should be discarded.",
            "Before the first brew, unpack all accessories: the portafilter, one single-shot basket, "
            "one double-shot basket, a stainless-steel tamper, a 450 ml milk jug and a measuring scoop.",
        ],
    ),
    (
        "First Use and Brewing",
        [
            "Before making your first coffee, run a rinse cycle: fill the tank, place a large cup "
            "under the group head, and press and hold the Brew button for three seconds. Hot water "
            "will flow for about 40 seconds. Repeat the rinse cycle once more if the machine has not "
            "been used for more than a week.",
            "The Aurora X200 heats up in 40 seconds from cold. The Ready light turns solid green when "
            "the machine reaches brewing temperature. The pump delivers 15 bar of pressure during "
            "extraction, and the thermostat holds water temperature at 93 degrees Celsius.",
            "The factory presets are 30 ml for a single shot and 60 ml for a double shot. To change "
            "the volume, hold the Single or Double button during a brew until you reach the volume you "
            "want, then release it; the new volume is stored automatically. For best results, use a "
            "medium-fine grind and dose 9 g of coffee for the single basket and 18 g for the double "
            "basket. Tamp firmly and evenly with about 15 kg of pressure.",
            "A good espresso takes between 25 and 30 seconds to extract. If the shot runs faster than "
            "20 seconds, use a finer grind; if it takes longer than 35 seconds, use a coarser grind.",
        ],
    ),
    (
        "Milk Frothing",
        [
            "The steam wand lets you texture milk for cappuccinos and lattes. Press the Steam button "
            "and wait for the Steam light to turn solid blue. The boiler needs about 25 seconds to "
            "switch from brewing to steaming temperature. Do not turn the steam dial until the light "
            "is solid, otherwise the wand may spit hot water.",
            "Before steaming, point the wand at the drip tray and open the steam dial for 3 seconds to "
            "purge any condensed water. Submerge the wand tip just below the milk surface, tilt the "
            "jug slightly, and open the dial fully. Lower the jug as the milk expands to create foam.",
            "Stop steaming when the milk reaches between 60 and 65 degrees Celsius, which is when the "
            "side of the jug becomes too hot to hold comfortably for more than a couple of seconds. "
            "Overheating milk above 70 degrees Celsius makes it taste flat and burnt. Always use cold, "
            "fresh milk straight from the refrigerator; whole milk gives the creamiest foam, but oat "
            "and soy drinks marketed for baristas also work.",
            "After every use, wipe the wand with a damp cloth and purge it for 2 seconds again. Dried "
            "milk inside the wand tip is the most common cause of weak steam.",
        ],
    ),
    (
        "Cleaning and Maintenance",
        [
            "Empty and rinse the drip tray and the used-coffee basket after each day of use. The drip "
            "tray has a red float that pops up when the tray is full; empty it at that point. Wash "
            "the tray, portafilter and baskets in warm soapy water; they are not dishwasher safe.",
            "Backflush the group head once a week using the supplied blind basket and one Aurora CT-10 "
            "cleaning tablet. Run five cycles of 10 seconds each with the tablet, then rinse with five "
            "more cycles of clear water.",
            "Descale the machine every 3 months, or after every 200 shots, whichever comes first. Mix "
            "100 ml of Aurora DS-5 descaling solution with 1 litre of fresh water, pour it into the "
            "tank and run the Descale program by holding the Steam and Brew buttons together for five "
            "seconds. The program takes about 20 minutes. Afterwards flush the tank with two full "
            "tanks of fresh water. Never use vinegar, which can damage the seals.",
            "Replace the water filter cartridge every 60 days. Soak the new cartridge in cold water "
            "for 5 minutes before inserting it. If you live in an area with very hard water, replace "
            "it every 30 days.",
        ],
    ),
    (
        "Troubleshooting",
        [
            "Error E1 flashes when the water tank is empty or not seated properly. Refill the tank, "
            "push it firmly down onto its base, and press Brew to resume. Error E2 means the boiler "
            "has overheated. Switch the machine off at the wall and wait 20 minutes before turning it "
            "on again. If E2 reappears, descale the machine. Error E3 indicates a pump fault. Do not "
            "keep pressing buttons; switch off, unplug the machine and contact customer support.",
            "If the espresso has little or thin crema, the coffee is probably stale or ground too "
            "coarse. Use beans roasted within the last four weeks and adjust the grind finer. If no "
            "coffee comes out, the group head screen may be blocked; run a backflush with a cleaning "
            "tablet. If the portafilter leaks around the edge, check that the basket is correctly "
            "seated and remove any grounds from the rim.",
            "If there is no steam, make sure the Steam light is solid blue, purge the wand, and use a "
            "pin to clear the tip holes. If the machine makes a loud buzzing noise, the tank is "
            "probably empty or an air lock has formed; refill the tank and run a rinse cycle.",
            "The machine switches itself into standby after 30 minutes of inactivity to save energy. "
            "Press any button to wake it.",
        ],
    ),
    (
        "Warranty and Support",
        [
            "The Aurora X200 is covered by a 24-month limited warranty from the date of purchase. The "
            "warranty covers defects in materials and workmanship under normal household use. "
            "Accessories such as the milk jug, tamper and water filter are covered for 90 days.",
            "Register your machine at the Aurora Coffee website within 30 days of purchase to extend "
            "the warranty to 36 months at no cost. Keep your receipt; proof of purchase is required "
            "for any claim.",
            "The warranty does not cover damage caused by scale build-up where the machine has not "
            "been descaled as described in this manual, damage from using unapproved cleaning "
            "products, commercial use, or accidental drops. Cosmetic wear on the exterior is also "
            "excluded.",
            "To make a claim, call customer support on 1-800-555-0142, Monday to Friday, 9 am to 6 pm "
            "Eastern Time, or write to support@aurora-coffee.example. Please have your serial number "
            "ready; it is printed on a label under the water tank. Repaired or replaced units carry "
            "only the remainder of the original warranty period. Do not return the machine to the "
            "store; support will arrange a prepaid courier collection.",
        ],
    ),
]

HARBORLINE_PAGES = [
    (
        "Account Overview",
        [
            "Harborline offers two savings products: the Harbor Saver account and the Harbor Plus "
            "account. To open an account you must be at least 18 years old, hold a valid "
            "government-issued photo ID, and be a resident of the United States. Joint accounts may "
            "have up to two owners.",
            "The minimum opening deposit is $100 for the Harbor Saver and $500 for the Harbor Plus. "
            "There is no minimum balance requirement for the Harbor Saver, and it carries no monthly "
            "maintenance fee. The Harbor Plus has a monthly maintenance fee of $5, which is waived in "
            "any month where your daily balance stays at or above $2,500.",
            "Accounts are opened online or at any Harborline branch. We verify your identity before "
            "the account is activated, which usually takes one business day. Deposits are insured up "
            "to $250,000 per depositor, per ownership category, by the federal deposit insurance "
            "program.",
        ],
    ),
    (
        "Interest Rates",
        [
            "The Harbor Saver earns a variable annual percentage yield (APY) of 3.10% on all balances. "
            "The Harbor Plus earns 3.85% APY on the portion of the balance above $10,000, and 3.10% "
            "APY on the portion up to $10,000.",
            "Interest is compounded daily and credited to your account on the last day of each "
            "statement cycle. Interest is calculated on the collected balance, which excludes "
            "deposits that have not yet cleared. Funds deposited by check begin earning interest on "
            "the business day after the check clears.",
            "All rates are variable and may change at any time. We will notify you of a rate change at "
            "least 14 days before it takes effect, by email and in the online banking message centre. "
            "The APY shown assumes that interest remains on deposit until the end of the statement "
            "cycle; withdrawals may reduce earnings.",
            "Promotional bonus rates, when offered, apply only for the period stated in the promotion, "
            "and revert to the standard rate afterwards. Bonus rates are not guaranteed and are not "
            "available to accounts that were closed and reopened within the previous six months.",
        ],
    ),
    (
        "Withdrawals and Transfers",
        [
            "Federal rules allow up to six convenience withdrawals or transfers from a savings account "
            "per statement cycle. Convenience withdrawals include online transfers to other banks, "
            "bill payments and debit card purchases. If you exceed six in one cycle, we charge an "
            "excess withdrawal fee of $10 for each additional transaction. Withdrawals made in person "
            "at a branch or at an ATM do not count toward the limit.",
            "The daily ATM withdrawal limit is $600 per account. The daily limit for debit card "
            "purchases is $2,500. You can request a temporary limit increase by calling customer "
            "service; approval takes up to two business days.",
            "Wire transfers can be requested online or at a branch. Domestic wires cost $25 and "
            "international wires cost $40. Incoming wires are free. Wires submitted before 3 pm "
            "Eastern Time on a business day are sent the same day.",
            "Transfers between your own Harborline accounts are free and instant. External transfers "
            "via the ACH network are free and typically arrive within two to three business days. The "
            "maximum ACH transfer is $10,000 per day.",
        ],
    ),
    (
        "Fees and Dormant Accounts",
        [
            "An account is considered dormant if there has been no customer-initiated activity for 12 "
            "consecutive months. Interest credits and fees do not count as activity. Once an account "
            "is dormant, a dormancy fee of $8 per month is charged until the account is reactivated "
            "or the balance reaches zero. We will write to you at your last known address 60 days "
            "before the account becomes dormant.",
            "Paper statements cost $3 per month; electronic statements are free and are the default. "
            "If you close an account within 90 days of opening it, an early closure fee of $25 is "
            "deducted from the closing balance. Closing an account after 90 days is free.",
            "Harborline does not offer overdraft protection on savings accounts. A transaction that "
            "would take the balance below zero will be declined, and no fee is charged for the "
            "declined transaction. Returned deposit items are charged $12 each.",
            "Replacement debit cards are free for the first request each year; additional "
            "replacements cost $10. Expedited card delivery within two business days costs $20.",
        ],
    ),
    (
        "Disputes and Contact",
        [
            "If you notice an unauthorised or incorrect transaction on your statement, you must report "
            "it within 60 days of the statement date. After that period we may not be able to recover "
            "the funds. Report problems by calling 1-800-555-0177, which is staffed 24 hours a day, "
            "or by sending a secure message through online banking.",
            "We will investigate every dispute and complete our review within 10 business days. If we "
            "need more time, we will provisionally credit your account for the disputed amount within "
            "those 10 business days while we continue the investigation, which can take up to 45 days.",
            "To file a formal complaint, write to Harborline Customer Relations, PO Box 4410, "
            "Columbus, Ohio. We acknowledge written complaints within 5 business days and aim to "
            "resolve them within 30 days.",
            "This agreement is governed by the laws of the State of Ohio. Harborline may amend these "
            "terms with 30 days written notice. Continued use of the account after the effective date "
            "means you accept the amended terms.",
        ],
    ),
]

DOCUMENTS = [
    ("aurora-x200-manual.pdf", "Aurora X200 Espresso Machine - User Manual", AURORA_PAGES),
    ("harborline-savings-terms.pdf", "Harborline Savings Accounts - Terms and Conditions", HARBORLINE_PAGES),
]


def build_pdf(path: Path, running_title: str, pages) -> None:
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("H", parent=styles["Heading1"], fontSize=18, spaceAfter=14)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=11, leading=15, spaceAfter=9)

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.drawString(inch, LETTER[1] - 0.6 * inch, running_title)
        canvas.drawRightString(LETTER[0] - inch, 0.6 * inch, f"Page {doc.page}")
        canvas.restoreState()

    story = []
    for i, (title, paragraphs) in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.append(Paragraph(f"{i + 1}. {title}", heading))
        story.append(Spacer(1, 4))
        story.extend(Paragraph(p, body) for p in paragraphs)

    SimpleDocTemplate(str(path), pagesize=LETTER).build(story, onFirstPage=decorate, onLaterPages=decorate)

    # A logical page that overflowed would shift every page number after it,
    # and the eval set's page labels would silently be wrong.
    actual = len(PdfReader(str(path)).pages)
    if actual != len(pages):
        raise RuntimeError(f"{path.name}: expected {len(pages)} pages, got {actual}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, title, pages in DOCUMENTS:
        build_pdf(OUT_DIR / filename, title, pages)
        print(f"wrote {OUT_DIR / filename} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
