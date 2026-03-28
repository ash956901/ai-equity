"""
Pydantic models for FMP API responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date


# Company Information Models
class CompanyProfile(BaseModel):
    symbol: str
    price: Optional[float] = None
    beta: Optional[float] = None
    volAvg: Optional[int] = None
    mktCap: Optional[float] = None
    lastDiv: Optional[float] = None
    range: Optional[str] = None
    changes: Optional[float] = None
    companyName: Optional[str] = None
    currency: Optional[str] = None
    cik: Optional[str] = None
    isin: Optional[str] = None
    cusip: Optional[str] = None
    exchange: Optional[str] = None
    exchangeShortName: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    ceo: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    fullTimeEmployees: Optional[int] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    dcfDiff: Optional[float] = None
    dcf: Optional[float] = None
    image: Optional[str] = None
    ipoDate: Optional[str] = None
    defaultImage: Optional[bool] = None
    isEtf: Optional[bool] = None
    isActivelyTrading: Optional[bool] = None
    isAdr: Optional[bool] = None
    isFund: Optional[bool] = None


# Stock Quote Models
class StockQuote(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    changesPercentage: Optional[float] = None
    change: Optional[float] = None
    dayLow: Optional[float] = None
    dayHigh: Optional[float] = None
    yearHigh: Optional[float] = None
    yearLow: Optional[float] = None
    marketCap: Optional[float] = None
    priceAvg50: Optional[float] = None
    priceAvg200: Optional[float] = None
    exchange: Optional[str] = None
    volume: Optional[int] = None
    avgVolume: Optional[int] = None
    open: Optional[float] = None
    previousClose: Optional[float] = None
    eps: Optional[float] = None
    pe: Optional[float] = None
    earningsAnnouncement: Optional[str] = None
    sharesOutstanding: Optional[int] = None
    timestamp: Optional[int] = None


# Historical Price Data
class HistoricalPrice(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    adjClose: Optional[float] = None
    volume: int
    unadjustedVolume: Optional[int] = None
    change: Optional[float] = None
    changePercent: Optional[float] = None
    vwap: Optional[float] = None
    label: Optional[str] = None
    changeOverTime: Optional[float] = None


# Financial Statements Models
class IncomeStatement(BaseModel):
    date: str
    symbol: str
    reportedCurrency: Optional[str] = None
    cik: Optional[str] = None
    fillingDate: Optional[str] = None
    acceptedDate: Optional[str] = None
    calendarYear: Optional[str] = None
    period: Optional[str] = None
    revenue: Optional[float] = None
    costOfRevenue: Optional[float] = None
    grossProfit: Optional[float] = None
    grossProfitRatio: Optional[float] = None
    researchAndDevelopmentExpenses: Optional[float] = None
    generalAndAdministrativeExpenses: Optional[float] = None
    sellingAndMarketingExpenses: Optional[float] = None
    sellingGeneralAndAdministrativeExpenses: Optional[float] = None
    otherExpenses: Optional[float] = None
    operatingExpenses: Optional[float] = None
    costAndExpenses: Optional[float] = None
    interestIncome: Optional[float] = None
    interestExpense: Optional[float] = None
    depreciationAndAmortization: Optional[float] = None
    ebitda: Optional[float] = None
    ebitdaratio: Optional[float] = None
    operatingIncome: Optional[float] = None
    operatingIncomeRatio: Optional[float] = None
    totalOtherIncomeExpensesNet: Optional[float] = None
    incomeBeforeTax: Optional[float] = None
    incomeBeforeTaxRatio: Optional[float] = None
    incomeTaxExpense: Optional[float] = None
    netIncome: Optional[float] = None
    netIncomeRatio: Optional[float] = None
    eps: Optional[float] = None
    epsdiluted: Optional[float] = None
    weightedAverageShsOut: Optional[float] = None
    weightedAverageShsOutDil: Optional[float] = None
    link: Optional[str] = None
    finalLink: Optional[str] = None


class BalanceSheet(BaseModel):
    date: str
    symbol: str
    reportedCurrency: Optional[str] = None
    cik: Optional[str] = None
    fillingDate: Optional[str] = None
    acceptedDate: Optional[str] = None
    calendarYear: Optional[str] = None
    period: Optional[str] = None
    cashAndCashEquivalents: Optional[float] = None
    shortTermInvestments: Optional[float] = None
    cashAndShortTermInvestments: Optional[float] = None
    netReceivables: Optional[float] = None
    inventory: Optional[float] = None
    otherCurrentAssets: Optional[float] = None
    totalCurrentAssets: Optional[float] = None
    propertyPlantEquipmentNet: Optional[float] = None
    goodwill: Optional[float] = None
    intangibleAssets: Optional[float] = None
    goodwillAndIntangibleAssets: Optional[float] = None
    longTermInvestments: Optional[float] = None
    taxAssets: Optional[float] = None
    otherNonCurrentAssets: Optional[float] = None
    totalNonCurrentAssets: Optional[float] = None
    otherAssets: Optional[float] = None
    totalAssets: Optional[float] = None
    accountPayables: Optional[float] = None
    shortTermDebt: Optional[float] = None
    taxPayables: Optional[float] = None
    deferredRevenue: Optional[float] = None
    otherCurrentLiabilities: Optional[float] = None
    totalCurrentLiabilities: Optional[float] = None
    longTermDebt: Optional[float] = None
    deferredRevenueNonCurrent: Optional[float] = None
    deferredTaxLiabilitiesNonCurrent: Optional[float] = None
    otherNonCurrentLiabilities: Optional[float] = None
    totalNonCurrentLiabilities: Optional[float] = None
    otherLiabilities: Optional[float] = None
    capitalLeaseObligations: Optional[float] = None
    totalLiabilities: Optional[float] = None
    preferredStock: Optional[float] = None
    commonStock: Optional[float] = None
    retainedEarnings: Optional[float] = None
    accumulatedOtherComprehensiveIncomeLoss: Optional[float] = None
    othertotalStockholdersEquity: Optional[float] = None
    totalStockholdersEquity: Optional[float] = None
    totalEquity: Optional[float] = None
    totalLiabilitiesAndStockholdersEquity: Optional[float] = None
    minorityInterest: Optional[float] = None
    totalLiabilitiesAndTotalEquity: Optional[float] = None
    totalInvestments: Optional[float] = None
    totalDebt: Optional[float] = None
    netDebt: Optional[float] = None
    link: Optional[str] = None
    finalLink: Optional[str] = None


class CashFlowStatement(BaseModel):
    date: str
    symbol: str
    reportedCurrency: Optional[str] = None
    cik: Optional[str] = None
    fillingDate: Optional[str] = None
    acceptedDate: Optional[str] = None
    calendarYear: Optional[str] = None
    period: Optional[str] = None
    netIncome: Optional[float] = None
    depreciationAndAmortization: Optional[float] = None
    deferredIncomeTax: Optional[float] = None
    stockBasedCompensation: Optional[float] = None
    changeInWorkingCapital: Optional[float] = None
    accountsReceivables: Optional[float] = None
    inventory: Optional[float] = None
    accountsPayables: Optional[float] = None
    otherWorkingCapital: Optional[float] = None
    otherNonCashItems: Optional[float] = None
    netCashProvidedByOperatingActivities: Optional[float] = None
    investmentsInPropertyPlantAndEquipment: Optional[float] = None
    acquisitionsNet: Optional[float] = None
    purchasesOfInvestments: Optional[float] = None
    salesMaturitiesOfInvestments: Optional[float] = None
    otherInvestingActivites: Optional[float] = None
    netCashUsedForInvestingActivites: Optional[float] = None
    debtRepayment: Optional[float] = None
    commonStockIssued: Optional[float] = None
    commonStockRepurchased: Optional[float] = None
    dividendsPaid: Optional[float] = None
    otherFinancingActivites: Optional[float] = None
    netCashUsedProvidedByFinancingActivities: Optional[float] = None
    effectOfForexChangesOnCash: Optional[float] = None
    netChangeInCash: Optional[float] = None
    cashAtEndOfPeriod: Optional[float] = None
    cashAtBeginningOfPeriod: Optional[float] = None
    operatingCashFlow: Optional[float] = None
    capitalExpenditure: Optional[float] = None
    freeCashFlow: Optional[float] = None
    link: Optional[str] = None
    finalLink: Optional[str] = None


# Key Metrics Models
class KeyMetrics(BaseModel):
    symbol: str
    date: str
    calendarYear: Optional[str] = None
    period: Optional[str] = None
    revenuePerShare: Optional[float] = None
    netIncomePerShare: Optional[float] = None
    operatingCashFlowPerShare: Optional[float] = None
    freeCashFlowPerShare: Optional[float] = None
    cashPerShare: Optional[float] = None
    bookValuePerShare: Optional[float] = None
    tangibleBookValuePerShare: Optional[float] = None
    shareholdersEquityPerShare: Optional[float] = None
    interestDebtPerShare: Optional[float] = None
    marketCap: Optional[float] = None
    enterpriseValue: Optional[float] = None
    peRatio: Optional[float] = None
    priceToSalesRatio: Optional[float] = None
    pocfratio: Optional[float] = None
    pfcfRatio: Optional[float] = None
    pbRatio: Optional[float] = None
    ptbRatio: Optional[float] = None
    evToSales: Optional[float] = None
    enterpriseValueOverEBITDA: Optional[float] = None
    evToOperatingCashFlow: Optional[float] = None
    evToFreeCashFlow: Optional[float] = None
    earningsYield: Optional[float] = None
    freeCashFlowYield: Optional[float] = None
    debtToEquity: Optional[float] = None
    debtToAssets: Optional[float] = None
    netDebtToEBITDA: Optional[float] = None
    currentRatio: Optional[float] = None
    interestCoverage: Optional[float] = None
    incomeQuality: Optional[float] = None
    dividendYield: Optional[float] = None
    payoutRatio: Optional[float] = None
    salesGeneralAndAdministrativeToRevenue: Optional[float] = None
    researchAndDdevelopementToRevenue: Optional[float] = None
    intangiblesToTotalAssets: Optional[float] = None
    capexToOperatingCashFlow: Optional[float] = None
    capexToRevenue: Optional[float] = None
    capexToDepreciation: Optional[float] = None
    stockBasedCompensationToRevenue: Optional[float] = None
    grahamNumber: Optional[float] = None
    roic: Optional[float] = None
    returnOnTangibleAssets: Optional[float] = None
    grahamNetNet: Optional[float] = None
    workingCapital: Optional[float] = None
    tangibleAssetValue: Optional[float] = None
    netCurrentAssetValue: Optional[float] = None
    investedCapital: Optional[float] = None
    averageReceivables: Optional[float] = None
    averagePayables: Optional[float] = None
    averageInventory: Optional[float] = None
    daysSalesOutstanding: Optional[float] = None
    daysPayablesOutstanding: Optional[float] = None
    daysOfInventoryOnHand: Optional[float] = None
    receivablesTurnover: Optional[float] = None
    payablesTurnover: Optional[float] = None
    inventoryTurnover: Optional[float] = None
    roe: Optional[float] = None
    capexPerShare: Optional[float] = None


# Financial Ratios
class FinancialRatios(BaseModel):
    symbol: str
    date: str
    calendarYear: Optional[str] = None
    period: Optional[str] = None
    currentRatio: Optional[float] = None
    quickRatio: Optional[float] = None
    cashRatio: Optional[float] = None
    daysOfSalesOutstanding: Optional[float] = None
    daysOfInventoryOutstanding: Optional[float] = None
    operatingCycle: Optional[float] = None
    daysOfPayablesOutstanding: Optional[float] = None
    cashConversionCycle: Optional[float] = None
    grossProfitMargin: Optional[float] = None
    operatingProfitMargin: Optional[float] = None
    pretaxProfitMargin: Optional[float] = None
    netProfitMargin: Optional[float] = None
    effectiveTaxRate: Optional[float] = None
    returnOnAssets: Optional[float] = None
    returnOnEquity: Optional[float] = None
    returnOnCapitalEmployed: Optional[float] = None
    netIncomePerEBT: Optional[float] = None
    ebtPerEbit: Optional[float] = None
    ebitPerRevenue: Optional[float] = None
    debtRatio: Optional[float] = None
    debtEquityRatio: Optional[float] = None
    longTermDebtToCapitalization: Optional[float] = None
    totalDebtToCapitalization: Optional[float] = None
    interestCoverage: Optional[float] = None
    cashFlowToDebtRatio: Optional[float] = None
    companyEquityMultiplier: Optional[float] = None
    receivablesTurnover: Optional[float] = None
    payablesTurnover: Optional[float] = None
    inventoryTurnover: Optional[float] = None
    fixedAssetTurnover: Optional[float] = None
    assetTurnover: Optional[float] = None
    operatingCashFlowPerShare: Optional[float] = None
    freeCashFlowPerShare: Optional[float] = None
    cashPerShare: Optional[float] = None
    payoutRatio: Optional[float] = None
    operatingCashFlowSalesRatio: Optional[float] = None
    freeCashFlowOperatingCashFlowRatio: Optional[float] = None
    cashFlowCoverageRatios: Optional[float] = None
    shortTermCoverageRatios: Optional[float] = None
    capitalExpenditureCoverageRatio: Optional[float] = None
    dividendPaidAndCapexCoverageRatio: Optional[float] = None
    dividendPayoutRatio: Optional[float] = None
    priceBookValueRatio: Optional[float] = None
    priceToBookRatio: Optional[float] = None
    priceToSalesRatio: Optional[float] = None
    priceEarningsRatio: Optional[float] = None
    priceToFreeCashFlowsRatio: Optional[float] = None
    priceToOperatingCashFlowsRatio: Optional[float] = None
    priceCashFlowRatio: Optional[float] = None
    priceEarningsToGrowthRatio: Optional[float] = None
    priceSalesRatio: Optional[float] = None
    dividendYield: Optional[float] = None
    enterpriseValueMultiple: Optional[float] = None
    priceFairValue: Optional[float] = None


# Earnings & Calendar
class EarningsCalendar(BaseModel):
    date: str
    symbol: str
    eps: Optional[float] = None
    epsEstimated: Optional[float] = None
    time: Optional[str] = None
    revenue: Optional[float] = None
    revenueEstimated: Optional[float] = None
    updatedFromDate: Optional[str] = None
    fiscalDateEnding: Optional[str] = None


# Stock News
class StockNews(BaseModel):
    symbol: str
    publishedDate: str
    title: str
    image: Optional[str] = None
    site: Optional[str] = None
    text: Optional[str] = None
    url: str


# Dividend Data
class DividendData(BaseModel):
    date: str
    label: Optional[str] = None
    adjDividend: float
    dividend: float
    recordDate: Optional[str] = None
    paymentDate: Optional[str] = None
    declarationDate: Optional[str] = None


# Analyst Estimates
class AnalystEstimates(BaseModel):
    symbol: str
    date: str
    estimatedRevenueLow: Optional[float] = None
    estimatedRevenueHigh: Optional[float] = None
    estimatedRevenueAvg: Optional[float] = None
    estimatedEbitdaLow: Optional[float] = None
    estimatedEbitdaHigh: Optional[float] = None
    estimatedEbitdaAvg: Optional[float] = None
    estimatedEbitLow: Optional[float] = None
    estimatedEbitHigh: Optional[float] = None
    estimatedEbitAvg: Optional[float] = None
    estimatedNetIncomeLow: Optional[float] = None
    estimatedNetIncomeHigh: Optional[float] = None
    estimatedNetIncomeAvg: Optional[float] = None
    estimatedSgaExpenseLow: Optional[float] = None
    estimatedSgaExpenseHigh: Optional[float] = None
    estimatedSgaExpenseAvg: Optional[float] = None
    estimatedEpsAvg: Optional[float] = None
    estimatedEpsHigh: Optional[float] = None
    estimatedEpsLow: Optional[float] = None
    numberAnalystEstimatedRevenue: Optional[int] = None
    numberAnalystsEstimatedEps: Optional[int] = None


# Insider Trading
class InsiderTrading(BaseModel):
    symbol: str
    filingDate: str
    transactionDate: str
    reportingCik: str
    transactionType: str
    securitiesOwned: int
    companyCik: str
    reportingName: str
    typeOfOwner: str
    acquisitionOrDisposition: str
    formType: str
    securitiesTransacted: float
    price: Optional[float] = None
    securityName: str
    link: str


# Institutional Holdings
class InstitutionalHolding(BaseModel):
    symbol: str
    cik: str
    date: str
    investorName: str
    portfolioSize: Optional[float] = None
    change: Optional[float] = None
    shares: Optional[int] = None
    weightPercentage: Optional[float] = None
    putCallShare: Optional[str] = None


# Market Data
class MarketHours(BaseModel):
    stockExchangeName: str
    stockMarketHours: Dict[str, Any]
    stockMarketHolidays: List[str]
    isTheStockMarketOpen: bool
    isTheEuronextMarketOpen: bool
    isTheForexMarketOpen: bool
    isTheCryptoMarketOpen: bool


# Sector Performance
class SectorPerformance(BaseModel):
    sector: str
    changesPercentage: str


# Economic Indicators
class EconomicIndicator(BaseModel):
    date: str
    value: float


# Stock Screener Result
class ScreenerResult(BaseModel):
    symbol: str
    companyName: str
    marketCap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    beta: Optional[float] = None
    price: Optional[float] = None
    lastAnnualDividend: Optional[float] = None
    volume: Optional[int] = None
    exchange: Optional[str] = None
    exchangeShortName: Optional[str] = None
    country: Optional[str] = None
    isEtf: Optional[bool] = None
    isActivelyTrading: Optional[bool] = None


# ETF Data
class ETFHolding(BaseModel):
    asset: str
    name: Optional[str] = None
    sharesNumber: Optional[int] = None
    weightPercentage: Optional[float] = None
    marketValue: Optional[float] = None
    updated: Optional[str] = None


# Press Release
class PressRelease(BaseModel):
    symbol: str
    date: str
    title: str
    text: str


# Stock Split
class StockSplit(BaseModel):
    date: str
    label: str
    symbol: str
    numerator: float
    denominator: float


# Market Index
class MarketIndex(BaseModel):
    symbol: str
    name: str
    price: float
    changesPercentage: float
    change: float
    dayLow: float
    dayHigh: float
    yearHigh: float
    yearLow: float
    marketCap: Optional[float] = None
    priceAvg50: float
    priceAvg200: float
    volume: int
    avgVolume: int
    exchange: str
    open: float
    previousClose: float
    timestamp: int


# SEC Filings
class SECFiling(BaseModel):
    symbol: str
    cik: Optional[str] = None
    name: Optional[str] = None
    sicCode: Optional[str] = None
    industryTitle: Optional[str] = None
    businessAddress: Optional[str] = None
    phoneNumber: Optional[str] = None
    title: Optional[str] = None
    acceptedDate: Optional[str] = None
    filingDate: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    finalLink: Optional[str] = None


# IPO Calendar
class IPOCalendar(BaseModel):
    date: str
    company: str
    symbol: str
    exchange: str
    actions: str
    shares: Optional[int] = None
    priceRange: Optional[str] = None
    marketCap: Optional[float] = None


# Earnings Surprise
class EarningsSurprise(BaseModel):
    date: str
    symbol: str
    actualEarningResult: Optional[float] = None
    estimatedEarning: Optional[float] = None


# Price Target
class PriceTarget(BaseModel):
    symbol: str
    publishedDate: str
    newsURL: str
    newsTitle: str
    analystName: Optional[str] = None
    priceTarget: Optional[float] = None
    adjPriceTarget: Optional[float] = None
    priceWhenPosted: Optional[float] = None
    newsPublisher: Optional[str] = None
    newsBaseURL: Optional[str] = None
    analystCompany: Optional[str] = None


# Upgrades/Downgrades
class UpgradeDowngrade(BaseModel):
    symbol: str
    publishedDate: str
    newsURL: str
    newsTitle: str
    newsPublisher: Optional[str] = None
    newGrade: Optional[str] = None
    previousGrade: Optional[str] = None
    gradingCompany: Optional[str] = None
    action: Optional[str] = None
