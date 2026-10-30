CREATE OR REPLACE PROCEDURE adventureworks_dbo.uspgetemployeemanagers(IN par_businessentityid INTEGER, INOUT p_refcur refcursor)
AS 
$BODY$
BEGIN
    /* Use recursive query to list out all Employees required for a particular Manager */
    
    /*
    [9996 - Severity CRITICAL - Transformer error occurred in statement. Please submit report to developers.]
    WITH [EMP_cte]([BusinessEntityID], [OrganizationNode], [FirstName], [LastName], [JobTitle], [RecursionLevel]) -- CTE name and columns
        AS (
            SELECT e.[BusinessEntityID], e.[OrganizationNode], p.[FirstName], p.[LastName], e.[JobTitle], 0 -- Get the initial Employee
            FROM [HumanResources].[Employee] e
    			INNER JOIN [Person].[Person] as p
    			ON p.[BusinessEntityID] = e.[BusinessEntityID]
            WHERE e.[BusinessEntityID] = @BusinessEntityID
            UNION ALL
            SELECT e.[BusinessEntityID], e.[OrganizationNode], p.[FirstName], p.[LastName], e.[JobTitle], [RecursionLevel] + 1 -- Join recursive member to anchor
            FROM [HumanResources].[Employee] e
                INNER JOIN [EMP_cte]
                ON e.[OrganizationNode] = [EMP_cte].[OrganizationNode].GetAncestor(1)
                INNER JOIN [Person].[Person] p
                ON p.[BusinessEntityID] = e.[BusinessEntityID]
        )
        -- Join back to Employee to return the manager name
        SELECT [EMP_cte].[RecursionLevel], [EMP_cte].[BusinessEntityID], [EMP_cte].[FirstName], [EMP_cte].[LastName],
            [EMP_cte].[OrganizationNode].ToString() AS [OrganizationNode], p.[FirstName] AS 'ManagerFirstName', p.[LastName] AS 'ManagerLastName'  -- Outer select from the CTE
        FROM [EMP_cte]
            INNER JOIN [HumanResources].[Employee] e
            ON [EMP_cte].[OrganizationNode].GetAncestor(1) = e.[OrganizationNode]
            INNER JOIN [Person].[Person] p
            ON p.[BusinessEntityID] = e.[BusinessEntityID]
        ORDER BY [RecursionLevel], [EMP_cte].[OrganizationNode].ToString()
        OPTION (MAXRECURSION 25)
    */
    BEGIN
    END;
END;
$BODY$
LANGUAGE plpgsql;