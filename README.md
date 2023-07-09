# tdi-capstone-electric-vehicles
This project estimates charging costs of electric vehicles

Electric vehicles have gained popularity in recent years due to their eco-friendliness, low emissions, and reduced reliance on fossil fuels. However, one of the most important factors that determine the feasibility and affordability of electric vehicles is costs associated with them. This app estimates energy costs of electric vehicles using factors such as vehicle make/model, battery capacities, travel distances and local electricity prices. It may help the user to:

Decide what make/model to purchase, 
Compare costs, 
Plan trips efficiently, knowing battery limitations, 
Avoid running out of power

The app uses historical electricity prices for a list of cities extracted from bls.gov. Then it predicts the future prices per KWH with time series analysis.  Finally, the app uses the predicted prices and vehicle battery information to estimate the charging costs in the future. Full data pipeline is provided below.



