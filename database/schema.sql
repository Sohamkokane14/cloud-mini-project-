CREATE TABLE Items (
  ItemId        INT IDENTITY(1,1) PRIMARY KEY,
  Type          NVARCHAR(10)  NOT NULL CHECK (Type IN ('lost','found')),
  Title         NVARCHAR(100) NOT NULL,
  Description   NVARCHAR(500),
  Category      NVARCHAR(50)  NOT NULL,
  Location      NVARCHAR(100),
  ItemDate      DATE,
  ImageUrl      NVARCHAR(500),
  Tags          NVARCHAR(500),
  Caption       NVARCHAR(300),
  ReporterName  NVARCHAR(100),
  ReporterEmail NVARCHAR(150),
  Status        NVARCHAR(20)  NOT NULL DEFAULT 'open',
  CreatedAt     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE Matches (
  MatchId     INT IDENTITY(1,1) PRIMARY KEY,
  LostItemId  INT NOT NULL REFERENCES Items(ItemId),
  FoundItemId INT NOT NULL REFERENCES Items(ItemId),
  Score       FLOAT NOT NULL,
  Status      NVARCHAR(20) NOT NULL DEFAULT 'suggested',
  CreatedAt   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  CONSTRAINT UQ_Matches_Lost_Found UNIQUE (LostItemId, FoundItemId)
);

CREATE INDEX IX_Items_Type_Status ON Items(Type, Status);
