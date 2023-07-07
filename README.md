# tdi-capstone-electric-vehicles
This project estimates charging costs of electric vehicles

Electric vehicles have gained popularity in recent years due to their eco-friendliness, low emissions, and reduced reliance on fossil fuels. However, one of the most important factors that determine the feasibility and affordability of electric vehicles is costs associated with them. This app estimates energy costs of electric vehicles using factors such as vehicle make/model, battery capacities, travel distances and local electricity prices. It may help the user to:

Decide what make/model to purchase, 
Compare costs, 
Plan trips efficiently, knowing battery limitations, 
Avoid running out of power

The app first extracts historical electricity prices for a list of cities from bls.gov for the past up to 60 years. Then it predicts the future prices per KWH with time series analysis. To complete data requirements for the predictions, the app fills up missing historical prices by averaging the existing prices for other cities in the same geographical region, for the same time period. Finally, the app uses the predicted prices and vehicle battery information to estimate the charging costs in the future.
