import ch.qos.logback.classic.encoder.PatternLayoutEncoder
import ch.qos.logback.core.rolling.RollingFileAppender
import ch.qos.logback.core.rolling.SizeAndTimeBasedFNATP
import ch.qos.logback.core.rolling.TimeBasedRollingPolicy
import ch.qos.logback.classic.Level
import static ch.qos.logback.classic.Level.*

appender("AUTOMATION_ALL", RollingFileAppender) {
  prudent = true
  rollingPolicy(TimeBasedRollingPolicy) {
    fileNamePattern = "/home/osmc/osocoTest01/server/var/log/shortener/%d{yyy-MM-dd}/shortener-%i.log"
    timeBasedFileNamingAndTriggeringPolicy(SizeAndTimeBasedFNATP) {
      maxFileSize = "50MB"
    }
    maxHistory = 7
    cleanHistoryOnStart = true
  }
  encoder(PatternLayoutEncoder) {
    pattern = "%date [%thread] %level %logger{10} \\(%line\\): %msg%n"
  }
}

root(Level.toLevel("debug"), ["AUTOMATION_ALL"])
