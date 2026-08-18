<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{{LABEL}}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{{UV}}</string>
        <string>run</string>
        <string>agent-daily</string>
        <string>run</string>
        <string>{{JOB_ID}}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{{PROJECT_DIR}}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{{PATH}}</string>
        <key>HOME</key>
        <string>{{HOME}}</string>
    </dict>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{{HOUR}}</integer>
        <key>Minute</key>
        <integer>{{MINUTE}}</integer>
    </dict>

    <key>ThrottleInterval</key>
    <integer>300</integer>

    <key>ProcessType</key>
    <string>Background</string>

    <key>LowPriorityIO</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{{STDOUT}}</string>
    <key>StandardErrorPath</key>
    <string>{{STDERR}}</string>
</dict>
</plist>
