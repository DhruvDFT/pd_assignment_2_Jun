# Updated Engineer Configuration - 18 Individual Engineers
def init_data():
    global users
    users['admin'] = {
        'id': 'admin',
        'username': 'admin',
        'password': hash_pass('Vibhuaya@3006'),
        'is_admin': True,
        'exp': 5
    }
    
    # 18 Individual Engineers (split from pairs)
    engineer_data = [
        ('eng001', 'Kranthi'),
        ('eng002', 'Neela'),
        ('eng003', 'Bhanu'),
        ('eng004', 'Lokeshwari'),
        ('eng005', 'Nagesh'),
        ('eng006', 'VJ'),
        ('eng007', 'Pravalika'),
        ('eng008', 'Daniel'),
        ('eng009', 'Karthik'),
        ('eng010', 'Hema'),
        ('eng011', 'Naveen'),
        ('eng012', 'Srinivas'),
        ('eng013', 'Meera'),
        ('eng014', 'Suraj'),
        ('eng015', 'Akhil'),
        ('eng016', 'Vikas'),
        ('eng017', 'Sahith'),
        ('eng018', 'Sravan')
    ]
    
    for uid, display_name in engineer_data:
        users[uid] = {
            'id': uid,
            'username': uid,
            'display_name': display_name,
            'password': hash_pass('password123'),
            'is_admin': False,
            'exp': 3 + (int(uid[-2:]) % 4)  # Experience varies 3-6 years
        }

# Simple Questions - 18 per topic (Easy to understand)
QUESTIONS = {
    "floorplanning": [
        # Basic Level (Questions 1-6)
        "What is floorplanning in chip design? Explain the main steps involved in creating a floorplan.",
        
        "You have a chip with CPU, memory, and I/O blocks. How would you arrange them on the chip? Give reasons for your placement.",
        
        "What are the benefits of good floorplanning? List at least 4 advantages.",
        
        "Explain what utilization means in floorplanning. What happens if utilization is too high or too low?",
        
        "What is the difference between hard macros and soft macros? How do you place them differently?",
        
        "Describe what aspect ratio means in floorplanning. How does it affect your design?",
        
        # Intermediate Level (Questions 7-12)
        "Your chip has two voltage levels: 1.8V and 1.2V. How would you plan the floorplan to handle both voltages?",
        
        "What is congestion in chip design? How can good floorplanning help reduce congestion?",
        
        "Explain the concept of hierarchical floorplanning. When would you use this approach?",
        
        "What are power domains? How do you consider them during floorplanning?",
        
        "Describe the relationship between floorplanning and timing. How does placement affect timing?",
        
        "What is pin assignment? How does it relate to your floorplan decisions?",
        
        # Advanced Level (Questions 13-18)
        "Your design has both analog and digital circuits. How would you separate them in the floorplan?",
        
        "What is clock planning? How do you consider clock distribution during floorplanning?",
        
        "Explain thermal considerations in floorplanning. How do you prevent hot spots?",
        
        "What are the challenges in floorplanning for low power designs?",
        
        "How do you validate your floorplan? What checks do you perform?",
        
    ],
    
    "placement": [
        # Basic Level (Questions 1-6)
        "What is placement in chip design? Explain the difference between global placement and detailed placement.",
        
        "Why is timing important in placement? How does the distance between gates affect timing?",
        
        "What is utilization in placement? What is a good utilization target and why?",
        
        "Explain what congestion means in placement. How do you identify congested areas?",
        
        "What are the main objectives of placement optimization? List at least 4 goals.",
        
        "Describe the relationship between placement and power consumption. How can placement reduce power?",
        
        # Intermediate Level (Questions 7-12)
        "Your design has setup timing violations. How can you fix them using placement techniques?",
        
        "What is clock gating? How do you place clock gating cells effectively?",
        
        "Explain the concept of placement density. How do you manage high-density areas?",
        
        "What are high fanout nets? How do you handle them during placement?",
        
        "Describe the impact of placement on routing. How do you ensure good routability?",
        
        "What is the difference between timing-driven and congestion-driven placement?",
        
        # Advanced Level (Questions 13-18)
        "How do you place memory blocks optimally? What factors do you consider?",
        
        "What are multi-Vt cells? How do you use them in placement for power optimization?",
        
        "Explain placement techniques for handling multiple clock domains.",
        
        "How do you optimize placement for manufacturability and yield?",
        
        "What is incremental placement? When do you use it?",
        
        "Describe placement considerations for DFT (Design for Test) structures."
    ],
    
    "routing": [
        # Basic Level (Questions 1-6)
        "What is routing in chip design? Explain the difference between global routing and detailed routing.",
        
        "What are DRC violations? Name 5 common types of DRC violations in routing.",
        
        "Explain what metal layers are used for. How do you decide which layer to use for a net?",
        
        "What is via? Why do we need vias in routing? What are the rules for via placement?",
        
        "Describe the concept of wire width and spacing. Why are these important in routing?",
        
        "What is the difference between signal routing and power routing?",
        
        # Intermediate Level (Questions 7-12)
        "Your design has many short violations. What steps would you take to fix them?",
        
        "What is crosstalk? How does routing affect crosstalk and how can you minimize it?",
        
        "Explain clock routing. What makes clock routing different from signal routing?",
        
        "What is antenna effect? How do you prevent antenna violations during routing?",
        
        "Describe metal density rules. Why do foundries require minimum metal density?",
        
        "What is electromigration? How do you design routing to prevent EM violations?",
        
        # Advanced Level (Questions 13-18)
        "How do you route high-speed differential signals? What special considerations are needed?",
        
        "What is double patterning? How does it affect your routing strategy?",
        
        "Explain power grid design. How do you ensure adequate power delivery?",
        
        "What are the challenges in routing for advanced technology nodes (7nm, 5nm)?",
        
        "How do you handle routing convergence issues? What techniques help achieve 100% routing?",
        
        "Describe routing optimization techniques for timing closure."
    ]
}
