FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /workspace
COPY pom.xml .
COPY src ./src
RUN mvn -B -DskipTests package

FROM eclipse-temurin:17-jre

WORKDIR /app
COPY --from=build /workspace/target/storex-backend.jar /app/storex-backend.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/storex-backend.jar"]
