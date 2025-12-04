from datetime import datetime, timedelta

MOCK_DATABASE = {
    # Product Catalog - Available insurance products
    "products": {
        "PROD001": {
            "product_id": "PROD001",
            "product_name": "Family Health Shield",
            "product_type": "Health Insurance",
            "base_premium": 25000,
            "sum_assured_options": [300000, 500000, 1000000],
            "features": ["Hospitalization", "Pre-post hospitalization", "Day care procedures"],
            "eligibility": {"min_age": 18, "max_age": 65}
        },
        "PROD002": {
            "product_id": "PROD002",
            "product_name": "Super Health Shield",
            "product_type": "Health Insurance",
            "base_premium": 40000,
            "sum_assured_options": [1000000, 1500000, 2000000],
            "features": ["No room rent capping", "Maternity cover", "Critical illness rider", "All PROD001 features"],
            "eligibility": {"min_age": 18, "max_age": 65}
        },
        "PROD003": {
            "product_id": "PROD003",
            "product_name": "Term Life Protector",
            "product_type": "Life Insurance",
            "base_premium": 15000,
            "sum_assured_options": [5000000, 10000000, 15000000],
            "features": ["Death benefit", "Terminal illness"],
            "eligibility": {"min_age": 18, "max_age": 60}
        },
        "PROD004": {
            "product_id": "PROD004",
            "product_name": "Premium Term Life",
            "product_type": "Life Insurance",
            "base_premium": 30000,
            "sum_assured_options": [10000000, 20000000, 30000000],
            "features": ["Accidental death benefit", "Critical illness rider", "Premium waiver", "All PROD003 features"],
            "eligibility": {"min_age": 18, "max_age": 60}
        },
        "PROD005": {
            "product_id": "PROD005",
            "product_name": "Comprehensive Car Cover",
            "product_type": "Motor Insurance",
            "base_premium": 18000,
            "sum_assured_options": [500000, 800000, 1200000],
            "features": ["Own damage", "Third party", "Personal accident"],
            "eligibility": {"vehicle_age_max": 15}
        },
        "PROD006": {
            "product_id": "PROD006",
            "product_name": "Zero Depreciation Cover",
            "product_type": "Motor Insurance",
            "base_premium": 28000,
            "sum_assured_options": [800000, 1000000, 1500000],
            "features": ["Zero depreciation", "Engine protection", "Roadside assistance", "All PROD005 features"],
            "eligibility": {"vehicle_age_max": 10}
        },
        "PROD007": {
            "product_id": "PROD007",
            "product_name": "Senior Citizen Health Care",
            "product_type": "Health Insurance",
            "base_premium": 45000,
            "sum_assured_options": [500000, 1000000],
            "features": ["Pre-existing disease cover", "AYUSH treatment", "Home healthcare", "No medical tests up to 70 years"],
            "eligibility": {"min_age": 60, "max_age": 80}
        }
    },
    
    # Customer Active Policies - What customers currently have
    "policies": {
        "POL-001": {
            "policy_id": "POL-001",
            "customer_id": "CUST001",
            "product_id": "PROD001",  # Links to product catalog
            "policy_number": "HLT/2024/001234",
            "premium_paid": 25000,
            "sum_assured": 500000,
            "start_date": "2024-01-15",
            "end_date": "2025-12-14",
            "claim_history": []
        },
        "POL-002": {
            "policy_id": "POL-002",
            "customer_id": "CUST001",
            "product_id": "PROD003",
            "policy_number": "LIFE/2023/005678",
            "premium_paid": 15000,
            "sum_assured": 10000000,
            "start_date": "2023-06-01",
            "end_date": "2026-01-02",
            "claim_history": []
        },
        "POL003": {
            "policy_id": "POL003",
            "customer_id": "CUST002",
            "product_id": "PROD005",
            "policy_number": "MTR/2024/009876",
            "premium_paid": 18000,
            "sum_assured": 800000,
            "start_date": "2024-03-10",
            "end_date": "2025-12-09",
            "claim_history": [{"date": "2024-08-15", "amount": 25000, "type": "Own damage"}]
        },
        "POL004": {
            "policy_id": "POL004",
            "customer_id": "CUST003",
            "product_id": "PROD001",
            "policy_number": "HLT/2024/002345",
            "premium_paid": 12000,
            "sum_assured": 300000,
            "start_date": "2024-02-20",
            "end_date": "2025-12-19",
            "claim_history": []
        }
    },
    
    # Customers
    "customers": {
        "CUST001": {
            "customer_id": "CUST001",
            "name": "Korathandavam",
            "email": "korathandavam@email.com",
            "phone": "+919123561817",
            "age": 27,
            "city": "Salem",
            "active_policies": ["POL-001", "POL-002"]
        },
        "CUST002": {
            "customer_id": "CUST002",
            "name": "kaveera",
            "email": "kaveera@email.com",
            "phone": "+919123561817",
            "age": 30,
            "city": "Salem",
            "active_policies": ["POL003"]
        },
        "CUST003": {
            "customer_id": "CUST003",
            "name": "Reeshwar",
            "email": "reeshwar@email.com",
            "phone": "+919123561817",
            "age": 57,
            "city": "Bangalore",
            "active_policies": ["POL004"]
        }
    }
}


def get_customers_with_policy_ending_soon(database, days=30):
    ending_soon_customers = []
    today = datetime.today()
    for customer in database["customers"].values():
        for policy_id in customer["active_policies"]:
            policy = database["policies"].get(policy_id)
            if policy:
                end_date = datetime.strptime(policy["end_date"], "%Y-%m-%d")
                if 0 <= (end_date - today).days <= days:
                    ending_soon_customers.append(customer["phone"])
                    break  # Only need to add customer once
    return ending_soon_customers

ENDING_POLICY_CUSTOMERS = get_customers_with_policy_ending_soon(MOCK_DATABASE, days=30)

def get_customer_active_policies(phone):
    for customer in MOCK_DATABASE["customers"].values():
        if customer["phone"] == phone:
            policies = []
            for policy_id in customer["active_policies"]:
                policy = MOCK_DATABASE["policies"].get(policy_id)
                if policy:
                    product = MOCK_DATABASE["products"].get(policy["product_id"], {})
                    policy_info = f"""
                        product_id: {policy['product_id']}
                        premium_paid: {policy['premium_paid']}
                        sum_assured: {policy['sum_assured']}
                        start_date: {policy['start_date']}
                        end_date: {policy['end_date']}
                        """
                    policies.append(policy_info)
            return "\n".join(policies)
        
    return ""  # Return empty list if customer not found

def get_product_details() -> str:
    product_details = []
    for product in MOCK_DATABASE["products"].values():
        details = f"""
            product_id: {product['product_id']}
            product_name: {product['product_name']}
            product_type: {product['product_type']}
            base_premium: {product['base_premium']}
            sum_assured_options: {product['sum_assured_options']}
            features: {product['features']}
            eligibility: {product['eligibility']}
            """
        product_details.append(details)
    return "\n".join(product_details)
