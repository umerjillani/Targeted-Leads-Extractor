from fuzzywuzzy import fuzz
import pandas as pd

sheet = pd.read_csv(r"Data\Datasheet.csv")

from location_data import north_america  

# ----------- Country Aliases -----------
country_aliases = {
    "usa": "United States",
    "united states": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "america": "United States",
    "canada": "Canada",
    "ca": "Canada",
    "can": "Canada",
    "mexico": "Mexico",
    "mx": "Mexico",
    "mex": "Mexico",
    "belize": "Belize",
    "bz": "Belize",
    "guatemala": "Guatemala",
    "gt": "Guatemala",
    "honduras": "Honduras",
    "hn": "Honduras",
    "nicaragua": "Nicaragua",
    "ni": "Nicaragua",
    "costa rica": "Costa Rica",
    "cr": "Costa Rica",
    "panama": "Panama",
    "pa": "Panama"
}

# ----------- Helper Functions -----------
def normalize_country(country):
    """Normalize country name using aliases."""
    country = country.strip().lower()
    return country_aliases.get(country, country.title())

def match_location(user_location):
    user_location = user_location.strip().lower()
    matched_locations = []
    exact_threshold = 95
    state_threshold = 90
    code_threshold = 95

    parts = [part.strip() for part in user_location.split(",") if part.strip()]

    potential_state = ""
    potential_country = ""

    # Try to identify country and state from parts
    for i in range(len(parts) - 1, -1, -1):
        part = parts[i]
        normalized_part = normalize_country(part)
        for country in north_america.keys():
            if fuzz.ratio(normalized_part.lower(), country.lower()) >= 90 or normalized_part == country:
                potential_country = country
                if i > 0:
                    potential_state = parts[i - 1]
                break
        if potential_country:
            break

    if not potential_country:
        potential_state = parts[-1] if parts else user_location
        potential_country = ""

    if potential_country and not potential_state:
        for state in north_america[potential_country].keys():
            matched_locations.append(f"{state}, {potential_country}")
        return list(set(matched_locations))

    for country in north_america.keys():
        for state, code in north_america[country].items():
            state_lower = state.lower()
            code_lower = code.lower()
            if potential_state == state_lower or potential_state == code_lower:
                if not potential_country or potential_country == country:
                    return [f"{state}, {country}"]
            state_score = fuzz.ratio(potential_state, state_lower)
            code_score = fuzz.ratio(potential_state, code_lower)
            if state_score >= exact_threshold or code_score >= exact_threshold:
                if not potential_country or potential_country == country:
                    return [f"{state}, {country}"]
            if state_score >= state_threshold or code_score >= code_threshold:
                if not potential_country or potential_country == country:
                    matched_locations.append(f"{state}, {country}")

    if len(parts) > 2:
        for country in north_america.keys():
            for state, code in north_america[country].items():
                state_lower = state.lower()
                code_lower = code.lower()
                if state_lower in user_location or code_lower in user_location:
                    matched_locations.append(f"{state}, {country}")

    return list(set(matched_locations))

def is_location_match(location_str, state, code, country):
    location_str = location_str.lower().strip()
    state_lower = state.lower()
    code_lower = code.lower()
    country_normalized = normalize_country(country).lower()

    if state_lower == location_str or code_lower == location_str:
        return True

    # Normalize country in location string
    location_parts = [normalize_country(part) if part in country_aliases else part for part in location_str.split(",")]
    normalized_location = ", ".join(location_parts).lower()

    state_match = (
        f" {state_lower}," in f" {normalized_location}," or
        f" {state_lower} " in f" {normalized_location} " or
        f", {state_lower}," in f", {normalized_location}," or
        f", {state_lower} " in f", {normalized_location} " or
        normalized_location.endswith(f" {state_lower}") or
        normalized_location.endswith(f", {state_lower}")
    )

    code_match = (
        f" {code_lower}," in f" {normalized_location}," or
        f" {code_lower} " in f" {normalized_location} " or
        f", {code_lower}," in f", {normalized_location}," or
        f", {code_lower} " in f", {normalized_location} " or
        normalized_location.endswith(f" {code_lower}") or
        normalized_location.endswith(f", {code_lower}")
    )

    country_match = (
        f" {country_normalized}," in f" {normalized_location}," or
        f" {country_normalized} " in f" {normalized_location} " or
        f", {country_normalized}," in f", {normalized_location}," or
        f", {country_normalized} " in f", {normalized_location} " or
        normalized_location.endswith(f" {country_normalized}") or
        normalized_location.endswith(f", {country_normalized}")
    )

    if (state_match or code_match) and (country_match or "," not in normalized_location):
        return True

    return False

def check_location(row, matched_locations_data):
    location = str(row['Location']).lower().strip()
    if not location:
        return False

    for state, country, code in matched_locations_data:
        if is_location_match(location, state, code, country):
            return True
    return False

# ----------- Main Execution -----------
sheet['Industry'] = sheet['Industry'].fillna("").str.strip().str.lower()
sheet['Location'] = sheet['Location'].fillna("").str.strip().str.lower()

unique_industries = sheet['Industry'].unique()

try:
    no_of_leads = int(input("Enter the number of leads you want.\n"))
except ValueError:
    print("Please enter a valid number.")
    exit()

user_input = input("What specific industry? (comma-separated for multiple):\n").strip().lower()
user_state = input("In which state, country, or address do you want us to find leads?\n").strip()

industry_list = [ind.strip() for ind in user_input.split(",") if ind.strip()]
filename_industry = "leads" if not industry_list else "_".join(industry_list)

threshold = 70
matched_industries = sorted({
    unique_industry for industry in industry_list
    for unique_industry in unique_industries
    if fuzz.partial_ratio(industry, unique_industry) > threshold
})

matched_locations = match_location(user_state)

if matched_locations:
    print(f"\nMatched locations: {matched_locations}")
    confirm = input("\nDo these locations match your query? (y/n): ").strip().lower()
    if confirm == 'n':
        print("\nYou can exclude locations. Enter the location to exclude or type 'done' to proceed.")
        while True:
            exclude = input("Exclude location (or 'done'): ").strip().lower()
            if exclude == 'done':
                break
            if exclude in [loc.lower() for loc in matched_locations]:
                matched_locations = [loc for loc in matched_locations if loc.lower() != exclude]
                print(f"Excluded '{exclude}'. Updated locations: {matched_locations}")
            else:
                print(f"'{exclude}' not in matched locations. Try again.")
    elif confirm != 'y':
        print("\nInvalid input. Proceeding with industry filter only.")
        matched_locations = []
else:
    print("\nNo matching locations found. Proceeding with industry filter only.")

if matched_industries:
    print(f"\nMatched industries: {matched_industries}")
    confirm = input("\nDo these industries match your query? (y/n): ").strip().lower()
    if confirm == 'n':
        print("\nYou can exclude industries. Enter the industry to exclude or type 'done' to proceed.")
        while True:
            exclude = input("Exclude industry (or 'done'): ").strip().lower()
            if exclude == 'done':
                break
            if exclude in matched_industries:
                matched_industries.remove(exclude)
                print(f"Excluded '{exclude}'. Updated industries: {matched_industries}")
            else:
                print(f"'{exclude}' not in matched industries. Try again.")
    elif confirm != 'y':
        print("\nInvalid input. Operation cancelled. No CSV saved.")
        exit()

    if matched_industries:
        filtered = sheet[sheet['Industry'].isin(matched_industries)]
        print(f"\nAfter industry filter, found {len(filtered)} leads.")

        if matched_locations:
            matched_locations_data = []
            for loc in matched_locations:
                state, country = loc.split(", ")
                if country in north_america and state in north_america[country]:
                    code = north_america[country][state]
                    matched_locations_data.append((state, country, code))

            filtered = filtered[
                filtered.apply(lambda row: check_location(row, matched_locations_data), axis=1)
            ]
            print(f"After location filter, found {len(filtered)} leads.")

        if filtered.empty:
            print("\nNo leads match the selected industries and locations.")
        else:
            output = filtered.head(no_of_leads)
            filename = f"{filename_industry}_leads"
            if matched_locations:
                filename += f"_{user_state.replace(' ', '_').lower()}"
            output.to_csv(rf"Data\{filename}.csv", index=False)
            print(f"\nSaved {len(output)} leads to Data\{filename}.csv")
    else:
        print("\nNo industries left after exclusions. No CSV saved.")
else:
    print("\nNo matching industries found.") 